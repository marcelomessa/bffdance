"""
BFF Dance - Buffer Circular de Poses
Armazena histórico de poses para análise de movimento
"""
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Deque
import numpy as np

from .pose_detector import Pose


@dataclass
class TimestampedPose:
    """Pose com timestamp"""
    pose: Pose
    timestamp: float = field(default_factory=time.time)


class PoseBuffer:
    """
    Buffer circular para armazenar histórico de poses.
    Usado para:
    - Detectar movimento/stillness
    - Capturar sequência de poses para comparação
    - Suavizar detecções
    """

    def __init__(self, max_size: int = 90, max_duration_seconds: float = 3.0):
        """
        Args:
            max_size: Número máximo de poses no buffer
            max_duration_seconds: Duração máxima em segundos
        """
        self.max_size = max_size
        self.max_duration = max_duration_seconds
        self._buffer: Deque[TimestampedPose] = deque(maxlen=max_size)

    def add(self, pose: Pose) -> None:
        """Adiciona pose ao buffer"""
        self._buffer.append(TimestampedPose(pose=pose))
        self._cleanup_old()

    def _cleanup_old(self) -> None:
        """Remove poses mais antigas que max_duration"""
        now = time.time()
        while self._buffer and (now - self._buffer[0].timestamp) > self.max_duration:
            self._buffer.popleft()

    def get_latest(self, n: int = 1) -> List[Pose]:
        """Retorna as n poses mais recentes"""
        return [tp.pose for tp in list(self._buffer)[-n:]]

    def get_all(self) -> List[TimestampedPose]:
        """Retorna todas as poses com timestamps"""
        return list(self._buffer)

    def get_average_pose(self, n: int = 5) -> Optional[Pose]:
        """
        Calcula pose média das últimas n poses (suavização).
        Útil para reduzir ruído na detecção.
        """
        poses = self.get_latest(n)
        if not poses:
            return None

        if len(poses) == 1:
            return poses[0]

        # Média dos keypoints
        from .pose_detector import Keypoint

        avg_keypoints = []
        num_keypoints = len(poses[0].keypoints)

        for kp_idx in range(num_keypoints):
            x_vals = []
            y_vals = []
            conf_vals = []

            for pose in poses:
                if kp_idx < len(pose.keypoints):
                    kp = pose.keypoints[kp_idx]
                    if kp.confidence > 0.3:
                        x_vals.append(kp.x)
                        y_vals.append(kp.y)
                        conf_vals.append(kp.confidence)

            if x_vals:
                avg_keypoints.append(Keypoint(
                    x=np.mean(x_vals),
                    y=np.mean(y_vals),
                    confidence=np.mean(conf_vals),
                    name=poses[0].keypoints[kp_idx].name if kp_idx < len(poses[0].keypoints) else ""
                ))
            else:
                avg_keypoints.append(poses[0].keypoints[kp_idx] if kp_idx < len(poses[0].keypoints) else
                                    Keypoint(0, 0, 0, ""))

        # Média da bbox
        avg_bbox = (
            np.mean([p.bbox[0] for p in poses]),
            np.mean([p.bbox[1] for p in poses]),
            np.mean([p.bbox[2] for p in poses]),
            np.mean([p.bbox[3] for p in poses])
        )

        return Pose(
            keypoints=avg_keypoints,
            bbox=avg_bbox,
            confidence=np.mean([p.confidence for p in poses]),
            person_id=poses[0].person_id
        )

    def calculate_movement(self, n: int = 10) -> float:
        """
        Calcula quantidade de movimento nas últimas n poses.
        Retorna valor normalizado (0 = parado, 1+ = muito movimento).
        """
        poses = self.get_latest(n)
        if len(poses) < 2:
            return 0.0

        total_movement = 0.0
        count = 0

        for i in range(1, len(poses)):
            prev_pose = poses[i - 1]
            curr_pose = poses[i]

            # Calcular movimento dos keypoints principais
            for kp_idx in range(min(len(prev_pose.keypoints), len(curr_pose.keypoints))):
                prev_kp = prev_pose.keypoints[kp_idx]
                curr_kp = curr_pose.keypoints[kp_idx]

                if prev_kp.confidence > 0.3 and curr_kp.confidence > 0.3:
                    # Distância euclidiana
                    dist = np.sqrt((curr_kp.x - prev_kp.x) ** 2 +
                                   (curr_kp.y - prev_kp.y) ** 2)
                    total_movement += dist
                    count += 1

        if count == 0:
            return 0.0

        # Normalizar pelo número de comparações e tamanho médio da bbox
        avg_size = 200  # Tamanho aproximado de uma pessoa em pixels
        normalized = (total_movement / count) / avg_size

        return normalized

    def is_still(self, threshold: float = 0.02, frames: int = 30) -> bool:
        """
        Verifica se a pessoa está parada.

        Args:
            threshold: Limiar de movimento (menor = mais sensível)
            frames: Número de frames para analisar

        Returns:
            True se movimento está abaixo do threshold
        """
        if len(self._buffer) < frames:
            return False

        movement = self.calculate_movement(frames)
        return movement < threshold

    def get_snapshot(self) -> Optional[Pose]:
        """
        Captura "snapshot" da pose atual (média suavizada).
        Usado quando jogador termina seu turno.
        """
        return self.get_average_pose(n=10)

    def clear(self) -> None:
        """Limpa o buffer"""
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)


class MultiPlayerPoseBuffer:
    """Buffer de poses para múltiplos jogadores"""

    def __init__(self, num_players: int = 2, **kwargs):
        self.buffers = {i: PoseBuffer(**kwargs) for i in range(num_players)}

    def add(self, player_id: int, pose: Pose) -> None:
        """Adiciona pose para um jogador específico"""
        if player_id in self.buffers:
            self.buffers[player_id].add(pose)

    def add_all(self, poses: List[Pose]) -> None:
        """Adiciona poses de todos os jogadores detectados"""
        for pose in poses:
            if pose.person_id in self.buffers:
                self.buffers[pose.person_id].add(pose)

    def get_buffer(self, player_id: int) -> Optional[PoseBuffer]:
        """Retorna buffer de um jogador"""
        return self.buffers.get(player_id)

    def is_player_still(self, player_id: int, **kwargs) -> bool:
        """Verifica se jogador está parado"""
        buffer = self.buffers.get(player_id)
        if buffer:
            return buffer.is_still(**kwargs)
        return False

    def get_player_snapshot(self, player_id: int) -> Optional[Pose]:
        """Captura snapshot da pose de um jogador"""
        buffer = self.buffers.get(player_id)
        if buffer:
            return buffer.get_snapshot()
        return None

    def clear_all(self) -> None:
        """Limpa todos os buffers"""
        for buffer in self.buffers.values():
            buffer.clear()
