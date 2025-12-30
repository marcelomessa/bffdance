"""
BFF Dance - Detector de Poses usando Hailo 8 + YOLOv8
"""
import numpy as np
import cv2
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path

from hailo_platform import HEF, VDevice, HailoStreamInterface, ConfigureParams
from hailo_platform import InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams

from ..config.settings import settings, KEYPOINT_NAMES


@dataclass
class Keypoint:
    """Um keypoint detectado"""
    x: float
    y: float
    confidence: float
    name: str = ""


@dataclass
class Pose:
    """Pose completa de uma pessoa"""
    keypoints: List[Keypoint]
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    person_id: int = -1

    @property
    def center_x(self) -> float:
        """Retorna o centro X da bounding box"""
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def center_y(self) -> float:
        """Retorna o centro Y da bounding box"""
        return (self.bbox[1] + self.bbox[3]) / 2

    def get_keypoint(self, name: str) -> Optional[Keypoint]:
        """Retorna keypoint pelo nome"""
        for kp in self.keypoints:
            if kp.name == name:
                return kp
        return None

    def to_normalized_array(self) -> np.ndarray:
        """
        Converte pose para array normalizado (0-1) para comparação.
        Normaliza pela bounding box da pessoa.
        """
        if not self.keypoints:
            return np.array([])

        width = self.bbox[2] - self.bbox[0]
        height = self.bbox[3] - self.bbox[1]

        if width <= 0 or height <= 0:
            return np.array([])

        normalized = []
        for kp in self.keypoints:
            nx = (kp.x - self.bbox[0]) / width
            ny = (kp.y - self.bbox[1]) / height
            normalized.extend([nx, ny, kp.confidence])

        return np.array(normalized)


class PoseDetector:
    """Detector de poses usando Hailo 8 com YOLOv8 Pose"""

    def __init__(self):
        self.device: Optional[VDevice] = None
        self.hef: Optional[HEF] = None
        self.network_group = None
        self.input_vstream_info = None
        self.output_vstream_info = None
        self.input_vstreams_params = None
        self.output_vstreams_params = None

        self._input_shape: Tuple[int, int] = (640, 640)
        self._initialized = False

    def initialize(self) -> bool:
        """Inicializa o Hailo e carrega o modelo"""
        try:
            # Tentar carregar modelo otimizado para Pi primeiro
            model_path = settings.hailo.pose_model
            if not Path(model_path).exists():
                model_path = settings.hailo.pose_model_fallback

            if not Path(model_path).exists():
                print(f"[ERROR] Modelo não encontrado: {model_path}")
                return False

            print(f"[INFO] Carregando modelo: {model_path}")

            # Criar dispositivo virtual Hailo
            self.device = VDevice()

            # Carregar HEF
            self.hef = HEF(model_path)

            # Configurar rede
            configure_params = ConfigureParams.create_from_hef(
                self.hef, interface=HailoStreamInterface.PCIe
            )
            self.network_group = self.device.configure(self.hef, configure_params)[0]

            # Obter info dos streams
            self.input_vstream_info = self.hef.get_input_vstream_infos()[0]
            self.output_vstream_info = self.hef.get_output_vstream_infos()

            # Configurar parâmetros dos streams
            self.input_vstreams_params = InputVStreamParams.make_from_network_group(
                self.network_group, format_type=FormatType.UINT8
            )
            self.output_vstreams_params = OutputVStreamParams.make_from_network_group(
                self.network_group, format_type=FormatType.FLOAT32
            )

            # Obter shape de entrada - formato é (H, W, C)
            input_shape = self.input_vstream_info.shape
            self._input_shape = (input_shape[0], input_shape[1])  # height, width

            self._initialized = True
            print(f"[INFO] Hailo inicializado - Input shape: {self._input_shape}")
            return True

        except Exception as e:
            print(f"[ERROR] Falha ao inicializar Hailo: {e}")
            return False

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocessa frame para inferência"""
        h, w = self._input_shape

        # Redimensionar mantendo aspect ratio
        frame_h, frame_w = frame.shape[:2]
        scale = min(h / frame_h, w / frame_w)
        new_w = int(frame_w * scale)
        new_h = int(frame_h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Criar imagem com padding
        padded = np.full((h, w, 3), 114, dtype=np.uint8)
        pad_x = (w - new_w) // 2
        pad_y = (h - new_h) // 2
        padded[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized

        # Guardar informações para pós-processamento
        self._preprocess_info = {
            'scale': scale,
            'pad_x': pad_x,
            'pad_y': pad_y,
            'orig_w': frame_w,
            'orig_h': frame_h
        }

        return padded

    def postprocess(self, outputs: dict, confidence_threshold: float = None) -> List[Pose]:
        """
        Processa saída do modelo YOLOv8 Pose para extrair poses.

        O modelo tem saídas em 3 escalas (20x20, 40x40, 80x80), cada uma com:
        - conv*3: bbox regression (64 canais - distribution focal loss)
        - conv*4: objectness (1 canal)
        - conv*5: keypoints (51 canais = 17 keypoints * 3)
        """
        if confidence_threshold is None:
            confidence_threshold = settings.hailo.confidence_threshold

        poses = []
        all_detections = []

        try:
            # Escalas e strides do YOLOv8
            scales = [
                {"size": 80, "stride": 8},   # conv43, conv44, conv45
                {"size": 40, "stride": 16},  # conv57, conv58, conv59
                {"size": 20, "stride": 32},  # conv70, conv71, conv72
            ]

            # Agrupar outputs por escala
            scale_outputs = {}
            for name, data in outputs.items():
                # Squeeze batch dimension
                if len(data.shape) == 4:
                    data = data[0]

                h, w, c = data.shape
                key = f"{h}x{w}"
                if key not in scale_outputs:
                    scale_outputs[key] = {}

                # Classificar pelo número de canais
                if c == 64:
                    scale_outputs[key]['bbox'] = data
                elif c == 1:
                    scale_outputs[key]['obj'] = data
                elif c == 51:
                    scale_outputs[key]['kpts'] = data

            # Processar cada escala
            for scale_info in scales:
                size = scale_info["size"]
                stride = scale_info["stride"]
                key = f"{size}x{size}"

                if key not in scale_outputs:
                    continue

                scale_data = scale_outputs[key]
                if not all(k in scale_data for k in ['bbox', 'obj', 'kpts']):
                    continue

                obj_map = scale_data['obj']
                bbox_map = scale_data['bbox']
                kpts_map = scale_data['kpts']

                # Encontrar detecções com alta confiança
                for y in range(size):
                    for x in range(size):
                        obj_conf = float(obj_map[y, x, 0])

                        # Aplicar sigmoid se necessário (valores podem vir raw)
                        if obj_conf < -10 or obj_conf > 10:
                            obj_conf = 1 / (1 + np.exp(-np.clip(obj_conf, -10, 10)))
                        elif obj_conf < 0:
                            obj_conf = 1 / (1 + np.exp(-obj_conf))

                        if obj_conf < confidence_threshold:
                            continue

                        # Decodificar bbox usando DFL (Distribution Focal Loss)
                        # Simplificado: usar centro da célula + offset médio
                        cx = (x + 0.5) * stride
                        cy = (y + 0.5) * stride

                        # Estimar tamanho do bbox baseado nas features
                        bbox_feat = bbox_map[y, x, :]
                        # DFL: dividido em 4 grupos de 16 para l, t, r, b
                        try:
                            l = self._dfl_decode(bbox_feat[0:16]) * stride
                            t = self._dfl_decode(bbox_feat[16:32]) * stride
                            r = self._dfl_decode(bbox_feat[32:48]) * stride
                            b = self._dfl_decode(bbox_feat[48:64]) * stride
                        except:
                            l = t = r = b = 32  # fallback

                        x1 = cx - l
                        y1 = cy - t
                        x2 = cx + r
                        y2 = cy + b

                        # Decodificar keypoints
                        keypoints = []
                        kpts_data = kpts_map[y, x, :]

                        for i in range(17):
                            idx = i * 3
                            # Fórmula oficial do Hailo C++ postprocess:
                            # kpts_corrdinates *= 2
                            # kpts_corrdinates = strides[i] * (kpts_corrdinates - 0.5) + center_values
                            raw_kp_x = kpts_data[idx]
                            raw_kp_y = kpts_data[idx + 1]
                            kp_x = stride * (raw_kp_x * 2 - 0.5) + cx
                            kp_y = stride * (raw_kp_y * 2 - 0.5) + cy
                            kp_conf_raw = kpts_data[idx + 2]

                            # Sempre aplicar sigmoid para normalizar confiança (0-1)
                            kp_conf = 1 / (1 + np.exp(-np.clip(kp_conf_raw, -10, 10)))

                            keypoints.append({
                                'x': kp_x,
                                'y': kp_y,
                                'conf': kp_conf
                            })

                        all_detections.append({
                            'bbox': (x1, y1, x2, y2),
                            'conf': obj_conf,
                            'keypoints': keypoints
                        })

            # Aplicar NMS simples
            all_detections.sort(key=lambda d: d['conf'], reverse=True)
            kept = []

            for det in all_detections:
                # Verificar overlap com detecções já mantidas
                dominated = False
                for kept_det in kept:
                    iou = self._compute_iou(det['bbox'], kept_det['bbox'])
                    if iou > settings.hailo.iou_threshold:
                        dominated = True
                        break

                if not dominated:
                    kept.append(det)

            # Converter para Pose objects
            for det in kept:
                # Escalar coordenadas para frame original
                bbox = self._scale_bbox(det['bbox'])

                keypoints = []
                for i, kp in enumerate(det['keypoints']):
                    sx, sy = self._scale_coords(kp['x'], kp['y'])
                    keypoints.append(Keypoint(
                        x=sx,
                        y=sy,
                        confidence=kp['conf'],
                        name=KEYPOINT_NAMES[i] if i < len(KEYPOINT_NAMES) else f"kp_{i}"
                    ))

                poses.append(Pose(
                    keypoints=keypoints,
                    bbox=bbox,
                    confidence=det['conf']
                ))

            # Ordenar por posição X
            poses.sort(key=lambda p: p.center_x)

            for i, pose in enumerate(poses):
                pose.person_id = i

        except Exception as e:
            print(f"[WARN] Erro no pós-processamento: {e}")
            import traceback
            traceback.print_exc()

        return poses

    def _dfl_decode(self, feat: np.ndarray) -> float:
        """Decodifica Distribution Focal Loss para um valor"""
        # Softmax
        feat = np.exp(feat - np.max(feat))
        feat = feat / np.sum(feat)
        # Weighted sum
        return np.sum(feat * np.arange(len(feat)))

    def _compute_iou(self, box1: Tuple, box2: Tuple) -> float:
        """Calcula IoU entre duas bboxes"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0

    def _decode_bbox(self, bbox_data: np.ndarray) -> Tuple[float, float, float, float]:
        """Decodifica bounding box"""
        # Assumindo formato x1, y1, x2, y2
        return (float(bbox_data[0]), float(bbox_data[1]),
                float(bbox_data[2]), float(bbox_data[3]))

    def _scale_coords(self, x: float, y: float) -> Tuple[float, float]:
        """Converte coordenadas de inferência para coordenadas originais"""
        info = self._preprocess_info
        x = (x - info['pad_x']) / info['scale']
        y = (y - info['pad_y']) / info['scale']
        return x, y

    def _scale_bbox(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Converte bbox de inferência para coordenadas originais"""
        x1, y1 = self._scale_coords(bbox[0], bbox[1])
        x2, y2 = self._scale_coords(bbox[2], bbox[3])
        return (x1, y1, x2, y2)

    def detect(self, frame: np.ndarray) -> List[Pose]:
        """
        Detecta poses em um frame.

        Args:
            frame: Frame BGR do OpenCV

        Returns:
            Lista de poses detectadas, ordenadas por posição X
        """
        if not self._initialized:
            print("[WARN] Detector não inicializado")
            return []

        # Preprocessar
        input_data = self.preprocess(frame)

        # Inferência - ativar network group primeiro
        with self.network_group.activate():
            with InferVStreams(self.network_group,
                              self.input_vstreams_params,
                              self.output_vstreams_params) as pipeline:
                input_dict = {self.input_vstream_info.name: np.expand_dims(input_data, 0)}
                outputs = pipeline.infer(input_dict)

        # Pós-processar
        poses = self.postprocess(outputs)

        return poses

    def release(self):
        """Libera recursos"""
        if self.device:
            self.device = None
        self._initialized = False


class CameraCapture:
    """Captura de vídeo da câmera do Raspberry Pi usando Picamera2"""

    def __init__(self):
        self.picam2 = None
        self._initialized = False

    def initialize(self) -> bool:
        """Inicializa a câmera usando Picamera2"""
        try:
            from picamera2 import Picamera2
            from libcamera import Transform

            self.picam2 = Picamera2()

            # Usar modo 2304x1296 para campo de visão completo (full sensor)
            # Depois redimensiona para o tamanho desejado
            config = self.picam2.create_video_configuration(
                main={"size": (2304, 1296), "format": "RGB888"},
                controls={"FrameRate": 30},
                transform=Transform(hflip=0, vflip=0)  # Sem flip na captura
            )

            # Forçar uso do sensor completo (sem crop)
            self.picam2.configure(config)
            self.picam2.start()

            # Guardar tamanho de saída desejado
            self._output_size = (settings.camera.width, settings.camera.height)

            print(f"[INFO] Câmera Picamera2 inicializada: 2304x1296 (full FOV) -> {self._output_size}")

            self._initialized = True
            return True

        except Exception as e:
            print(f"[ERROR] Falha ao inicializar câmera: {e}")
            import traceback
            traceback.print_exc()
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Lê um frame da câmera"""
        if not self._initialized or self.picam2 is None:
            return False, None

        try:
            # Captura frame como numpy array (RGB)
            frame = self.picam2.capture_array()
            # Converter RGB para BGR (OpenCV format)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            # Redimensionar para tamanho de saída
            if hasattr(self, '_output_size'):
                frame_bgr = cv2.resize(frame_bgr, self._output_size)
            return True, frame_bgr
        except Exception as e:
            print(f"[WARN] Erro ao capturar frame: {e}")
            return False, None

    def release(self):
        """Libera a câmera"""
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except:
                pass
        self._initialized = False


def draw_poses(frame: np.ndarray, poses: List[Pose],
               show_skeleton: bool = True,
               show_keypoints: bool = True) -> np.ndarray:
    """
    Desenha poses no frame.

    Args:
        frame: Frame BGR
        poses: Lista de poses detectadas
        show_skeleton: Se deve desenhar as conexões do esqueleto
        show_keypoints: Se deve desenhar os pontos

    Returns:
        Frame com poses desenhadas
    """
    from ..config.settings import SKELETON_CONNECTIONS, PLAYER_COLORS

    output = frame.copy()

    for pose in poses:
        # Cor baseada no ID do jogador
        color_idx = pose.person_id % len(PLAYER_COLORS)
        color = PLAYER_COLORS[color_idx]

        # Desenhar bounding box (opcional, comentado)
        # x1, y1, x2, y2 = [int(v) for v in pose.bbox]
        # cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)

        # Converter keypoints para dict para acesso fácil
        kp_dict = {kp.name: kp for kp in pose.keypoints}

        # Desenhar esqueleto
        if show_skeleton:
            for start_idx, end_idx in SKELETON_CONNECTIONS:
                start_name = KEYPOINT_NAMES[start_idx]
                end_name = KEYPOINT_NAMES[end_idx]

                if start_name in kp_dict and end_name in kp_dict:
                    kp1 = kp_dict[start_name]
                    kp2 = kp_dict[end_name]

                    # Só desenhar se ambos keypoints tiverem confiança mínima
                    if kp1.confidence > 0.3 and kp2.confidence > 0.3:
                        pt1 = (int(kp1.x), int(kp1.y))
                        pt2 = (int(kp2.x), int(kp2.y))
                        cv2.line(output, pt1, pt2, color, 2)

        # Desenhar keypoints
        if show_keypoints:
            for kp in pose.keypoints:
                if kp.confidence > 0.3:
                    pt = (int(kp.x), int(kp.y))
                    cv2.circle(output, pt, 5, color, -1)
                    cv2.circle(output, pt, 5, (255, 255, 255), 1)

        # Label do jogador
        label = f"P{pose.person_id + 1}"
        label_pos = (int(pose.center_x) - 15, int(pose.bbox[1]) - 10)
        cv2.putText(output, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, 2)

    return output
