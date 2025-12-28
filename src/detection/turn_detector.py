"""
BFF Dance - Detector de Troca de Turno
Detecta quando um jogador termina seu turno (stillness ou gesto)
"""
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

from ..core.pose_detector import Pose
from ..core.pose_buffer import MultiPlayerPoseBuffer
from ..config.settings import settings


class TurnSignal(Enum):
    """Sinais de troca de turno"""
    NONE = "none"              # Nenhum sinal
    STILLNESS = "stillness"    # Parou de se mover
    GESTURE = "gesture"        # Fez gesto específico
    TIMEOUT = "timeout"        # Tempo esgotou


@dataclass
class TurnEvent:
    """Evento de troca de turno"""
    signal: TurnSignal
    player_id: int
    timestamp: float
    captured_pose: Optional[Pose] = None


class TurnDetector:
    """
    Detecta quando um jogador indica fim de turno.
    Suporta:
    - Stillness: ficar parado por X frames
    - Gesto: mão aberta, high-five no ar, etc.
    """

    def __init__(self, pose_buffer: MultiPlayerPoseBuffer):
        self.pose_buffer = pose_buffer

        # Configurações de stillness
        self.stillness_threshold = settings.gameplay.stillness_threshold
        self.stillness_frames = settings.gameplay.stillness_frames

        # Estado
        self._current_player = 0
        self._turn_start_time = time.time()
        self._stillness_counter = {0: 0, 1: 0}
        self._last_turn_event: Optional[TurnEvent] = None

    def update(self, poses: List[Pose]) -> Optional[TurnEvent]:
        """
        Atualiza detector com novas poses.

        Args:
            poses: Lista de poses detectadas no frame atual

        Returns:
            TurnEvent se turno deve trocar, None caso contrário
        """
        # Adicionar poses aos buffers
        self.pose_buffer.add_all(poses)

        # Verificar timeout
        elapsed = time.time() - self._turn_start_time
        max_turn_time = settings.gameplay.imitation_time_seconds * 2

        if elapsed > max_turn_time:
            return self._create_turn_event(TurnSignal.TIMEOUT)

        # Verificar stillness do jogador atual
        if self._check_stillness(self._current_player):
            return self._create_turn_event(TurnSignal.STILLNESS)

        # Verificar gesto de troca
        if self._check_gesture(poses):
            return self._create_turn_event(TurnSignal.GESTURE)

        return None

    def _check_stillness(self, player_id: int) -> bool:
        """Verifica se jogador está parado por tempo suficiente"""
        buffer = self.pose_buffer.get_buffer(player_id)
        if not buffer:
            return False

        if buffer.is_still(self.stillness_threshold, min(len(buffer), 30)):
            self._stillness_counter[player_id] += 1
        else:
            self._stillness_counter[player_id] = 0

        return self._stillness_counter[player_id] >= self.stillness_frames

    def _check_gesture(self, poses: List[Pose]) -> bool:
        """
        Verifica se jogador atual fez gesto de troca.
        Por enquanto: detecta mãos acima da cabeça.
        """
        for pose in poses:
            if pose.person_id != self._current_player:
                continue

            # Pegar keypoints relevantes
            kp_dict = {kp.name: kp for kp in pose.keypoints}

            nose = kp_dict.get("nose")
            left_wrist = kp_dict.get("left_wrist")
            right_wrist = kp_dict.get("right_wrist")

            if not all([nose, left_wrist, right_wrist]):
                continue

            # Verificar se ambas as mãos estão acima do nariz
            if (left_wrist.confidence > 0.5 and right_wrist.confidence > 0.5 and
                left_wrist.y < nose.y and right_wrist.y < nose.y):

                # E se as mãos estão próximas (high-five position)
                wrist_distance = abs(left_wrist.x - right_wrist.x)
                if wrist_distance < 100:  # pixels
                    return True

        return False

    def _create_turn_event(self, signal: TurnSignal) -> TurnEvent:
        """Cria evento de troca de turno"""
        # Capturar pose do jogador atual
        captured_pose = self.pose_buffer.get_player_snapshot(self._current_player)

        event = TurnEvent(
            signal=signal,
            player_id=self._current_player,
            timestamp=time.time(),
            captured_pose=captured_pose
        )

        # Trocar jogador
        self._switch_player()

        return event

    def _switch_player(self) -> None:
        """Troca para o próximo jogador"""
        self._current_player = 1 - self._current_player  # 0 <-> 1
        self._turn_start_time = time.time()
        self._stillness_counter = {0: 0, 1: 0}

    def get_current_player(self) -> int:
        """Retorna ID do jogador atual"""
        return self._current_player

    def get_turn_elapsed_time(self) -> float:
        """Retorna tempo decorrido no turno atual"""
        return time.time() - self._turn_start_time

    def get_turn_remaining_time(self) -> float:
        """Retorna tempo restante para imitar (se aplicável)"""
        elapsed = self.get_turn_elapsed_time()
        return max(0, settings.gameplay.imitation_time_seconds - elapsed)

    def force_switch(self) -> TurnEvent:
        """Força troca de turno (chamado externamente)"""
        return self._create_turn_event(TurnSignal.TIMEOUT)

    def reset(self, starting_player: int = 0) -> None:
        """Reseta detector para novo jogo"""
        self._current_player = starting_player
        self._turn_start_time = time.time()
        self._stillness_counter = {0: 0, 1: 0}
        self._last_turn_event = None
        self.pose_buffer.clear_all()


class GestureDetector:
    """
    Detecta gestos específicos nas poses.
    Usado para easter eggs e interações especiais.
    """

    @staticmethod
    def detect_heart(pose1: Pose, pose2: Pose, max_distance: float = 50) -> bool:
        """
        Detecta se dois jogadores estão fazendo um coração com as mãos.
        Cada um contribui com uma mão.
        """
        kp1 = {kp.name: kp for kp in pose1.keypoints}
        kp2 = {kp.name: kp for kp in pose2.keypoints}

        # Player 1: mão direita, Player 2: mão esquerda (ou vice-versa)
        combinations = [
            (kp1.get("right_wrist"), kp2.get("left_wrist")),
            (kp1.get("left_wrist"), kp2.get("right_wrist")),
        ]

        for wrist1, wrist2 in combinations:
            if not wrist1 or not wrist2:
                continue
            if wrist1.confidence < 0.5 or wrist2.confidence < 0.5:
                continue

            # Verificar proximidade
            distance = ((wrist1.x - wrist2.x) ** 2 +
                        (wrist1.y - wrist2.y) ** 2) ** 0.5

            if distance < max_distance:
                # Verificar se estão acima da linha dos ombros (posição de coração)
                shoulder1 = kp1.get("right_shoulder") or kp1.get("left_shoulder")
                shoulder2 = kp2.get("right_shoulder") or kp2.get("left_shoulder")

                if shoulder1 and shoulder2:
                    avg_shoulder_y = (shoulder1.y + shoulder2.y) / 2
                    avg_wrist_y = (wrist1.y + wrist2.y) / 2

                    if avg_wrist_y < avg_shoulder_y:  # Mãos acima dos ombros
                        return True

        return False

    @staticmethod
    def detect_high_five(pose1: Pose, pose2: Pose, max_distance: float = 80) -> bool:
        """Detecta high-five entre dois jogadores"""
        kp1 = {kp.name: kp for kp in pose1.keypoints}
        kp2 = {kp.name: kp for kp in pose2.keypoints}

        # Verificar todas as combinações de mãos
        wrists = [
            (kp1.get("right_wrist"), kp2.get("left_wrist")),
            (kp1.get("right_wrist"), kp2.get("right_wrist")),
            (kp1.get("left_wrist"), kp2.get("left_wrist")),
            (kp1.get("left_wrist"), kp2.get("right_wrist")),
        ]

        for w1, w2 in wrists:
            if not w1 or not w2:
                continue
            if w1.confidence < 0.5 or w2.confidence < 0.5:
                continue

            distance = ((w1.x - w2.x) ** 2 + (w1.y - w2.y) ** 2) ** 0.5

            if distance < max_distance:
                return True

        return False

    @staticmethod
    def detect_mirror_pose(pose1: Pose, pose2: Pose, threshold: float = 0.7) -> bool:
        """
        Detecta se dois jogadores estão em poses espelhadas.
        (Um é o reflexo do outro)
        """
        # Mapear keypoints espelhados
        mirror_map = {
            "left_shoulder": "right_shoulder",
            "right_shoulder": "left_shoulder",
            "left_elbow": "right_elbow",
            "right_elbow": "left_elbow",
            "left_wrist": "right_wrist",
            "right_wrist": "left_wrist",
            "left_hip": "right_hip",
            "right_hip": "left_hip",
            "left_knee": "right_knee",
            "right_knee": "left_knee",
        }

        kp1 = {kp.name: kp for kp in pose1.keypoints}
        kp2 = {kp.name: kp for kp in pose2.keypoints}

        # Normalizar poses
        def normalize(kp_dict, bbox):
            normalized = {}
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w <= 0 or h <= 0:
                return normalized

            for name, kp in kp_dict.items():
                if kp.confidence > 0.3:
                    normalized[name] = ((kp.x - bbox[0]) / w, (kp.y - bbox[1]) / h)
            return normalized

        norm1 = normalize(kp1, pose1.bbox)
        norm2 = normalize(kp2, pose2.bbox)

        if not norm1 or not norm2:
            return False

        # Comparar posições espelhadas
        matches = 0
        total = 0

        for name1, mirror_name in mirror_map.items():
            if name1 in norm1 and mirror_name in norm2:
                x1, y1 = norm1[name1]
                x2, y2 = norm2[mirror_name]

                # Espelhar x de pose2
                x2_mirrored = 1 - x2

                distance = ((x1 - x2_mirrored) ** 2 + (y1 - y2) ** 2) ** 0.5

                if distance < 0.3:  # Tolerância
                    matches += 1
                total += 1

        if total == 0:
            return False

        return (matches / total) >= threshold
