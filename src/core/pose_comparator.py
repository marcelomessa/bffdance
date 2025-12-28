"""
BFF Dance - Comparador de Poses
Calcula similaridade entre poses para pontuação
"""
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .pose_detector import Pose, Keypoint
from ..config.settings import settings, KEYPOINT_NAMES


@dataclass
class ComparisonResult:
    """Resultado da comparação entre duas poses"""
    overall_score: float          # Score geral (0-100)
    keypoint_scores: dict         # Score por keypoint
    angle_scores: dict            # Score por ângulo/articulação
    feedback: str                 # Feedback textual
    rating: str                   # "perfect", "good", "ok", "miss"


# Articulações importantes para dança (pares de keypoints para calcular ângulos)
JOINT_ANGLES = {
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_shoulder": ("left_hip", "left_shoulder", "left_elbow"),
    "right_shoulder": ("right_hip", "right_shoulder", "right_elbow"),
    "left_hip": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip": ("right_shoulder", "right_hip", "right_knee"),
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
}

# Pesos para cada grupo de keypoints (importância para a pontuação)
KEYPOINT_WEIGHTS = {
    # Braços são muito importantes para dança
    "left_wrist": 1.5,
    "right_wrist": 1.5,
    "left_elbow": 1.2,
    "right_elbow": 1.2,
    "left_shoulder": 1.0,
    "right_shoulder": 1.0,
    # Corpo
    "left_hip": 0.8,
    "right_hip": 0.8,
    # Pernas
    "left_knee": 0.7,
    "right_knee": 0.7,
    "left_ankle": 0.6,
    "right_ankle": 0.6,
    # Cabeça (menos importante para poses de dança)
    "nose": 0.3,
    "left_eye": 0.1,
    "right_eye": 0.1,
    "left_ear": 0.1,
    "right_ear": 0.1,
}


class PoseComparator:
    """Compara duas poses e calcula similaridade"""

    def __init__(self):
        self.angle_weight = 0.6  # Peso dos ângulos no score final
        self.position_weight = 0.4  # Peso das posições no score final

    def compare(self, pose1: Pose, pose2: Pose) -> ComparisonResult:
        """
        Compara duas poses e retorna score de similaridade.

        Args:
            pose1: Pose de referência (a ser imitada)
            pose2: Pose do jogador (tentando imitar)

        Returns:
            ComparisonResult com score e feedback
        """
        # Normalizar poses pela bounding box
        norm1 = self._normalize_pose(pose1)
        norm2 = self._normalize_pose(pose2)

        # Calcular scores de posição dos keypoints
        keypoint_scores = self._compare_keypoints(norm1, norm2)

        # Calcular scores dos ângulos das articulações
        angle_scores = self._compare_angles(pose1, pose2)

        # Calcular score geral ponderado
        position_score = self._weighted_average(keypoint_scores)
        angle_score = self._weighted_average_angles(angle_scores)

        overall_score = (
            position_score * self.position_weight +
            angle_score * self.angle_weight
        ) * 100

        # Determinar rating
        rating = self._get_rating(overall_score)

        # Gerar feedback
        feedback = self._generate_feedback(keypoint_scores, angle_scores, rating)

        return ComparisonResult(
            overall_score=overall_score,
            keypoint_scores=keypoint_scores,
            angle_scores=angle_scores,
            feedback=feedback,
            rating=rating
        )

    def _normalize_pose(self, pose: Pose) -> dict:
        """Normaliza pose para coordenadas 0-1 relativas à bounding box"""
        normalized = {}

        width = pose.bbox[2] - pose.bbox[0]
        height = pose.bbox[3] - pose.bbox[1]

        if width <= 0 or height <= 0:
            return normalized

        for kp in pose.keypoints:
            if kp.confidence > 0.3:
                nx = (kp.x - pose.bbox[0]) / width
                ny = (kp.y - pose.bbox[1]) / height
                normalized[kp.name] = (nx, ny, kp.confidence)

        return normalized

    def _compare_keypoints(self, norm1: dict, norm2: dict) -> dict:
        """Compara posições normalizadas dos keypoints"""
        scores = {}

        for name in KEYPOINT_NAMES:
            if name in norm1 and name in norm2:
                x1, y1, conf1 = norm1[name]
                x2, y2, conf2 = norm2[name]

                # Distância euclidiana normalizada
                dist = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

                # Converter distância para score (0-1)
                # dist=0 -> score=1, dist=1 -> score=0
                score = max(0, 1 - dist)

                # Ponderar pela confiança média
                confidence = (conf1 + conf2) / 2
                scores[name] = score * confidence
            else:
                scores[name] = 0.0

        return scores

    def _compare_angles(self, pose1: Pose, pose2: Pose) -> dict:
        """Compara ângulos das articulações"""
        scores = {}

        kp1_dict = {kp.name: kp for kp in pose1.keypoints}
        kp2_dict = {kp.name: kp for kp in pose2.keypoints}

        for joint_name, (p1, p2, p3) in JOINT_ANGLES.items():
            angle1 = self._calculate_angle(kp1_dict, p1, p2, p3)
            angle2 = self._calculate_angle(kp2_dict, p1, p2, p3)

            if angle1 is not None and angle2 is not None:
                # Diferença angular (0-180 graus)
                diff = abs(angle1 - angle2)
                # Normalizar: 0 graus de diferença = 1, 90 graus = 0
                score = max(0, 1 - diff / 90)
                scores[joint_name] = score
            else:
                scores[joint_name] = 0.0

        return scores

    def _calculate_angle(self, kp_dict: dict, p1: str, p2: str, p3: str) -> Optional[float]:
        """Calcula ângulo entre três keypoints"""
        if not all(k in kp_dict and kp_dict[k].confidence > 0.3 for k in [p1, p2, p3]):
            return None

        # Vetores
        v1 = np.array([kp_dict[p1].x - kp_dict[p2].x,
                       kp_dict[p1].y - kp_dict[p2].y])
        v2 = np.array([kp_dict[p3].x - kp_dict[p2].x,
                       kp_dict[p3].y - kp_dict[p2].y])

        # Ângulo em graus
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        cos_angle = np.clip(cos_angle, -1, 1)
        angle = np.degrees(np.arccos(cos_angle))

        return angle

    def _weighted_average(self, scores: dict) -> float:
        """Calcula média ponderada dos scores de keypoints"""
        total_weight = 0
        weighted_sum = 0

        for name, score in scores.items():
            weight = KEYPOINT_WEIGHTS.get(name, 0.5)
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0

    def _weighted_average_angles(self, scores: dict) -> float:
        """Calcula média dos scores de ângulos"""
        if not scores:
            return 0
        return sum(scores.values()) / len(scores)

    def _get_rating(self, score: float) -> str:
        """Determina rating baseado no score"""
        if score >= settings.gameplay.perfect_threshold * 100:
            return "perfect"
        elif score >= settings.gameplay.good_threshold * 100:
            return "good"
        elif score >= settings.gameplay.ok_threshold * 100:
            return "ok"
        else:
            return "miss"

    def _generate_feedback(self, kp_scores: dict, angle_scores: dict, rating: str) -> str:
        """Gera feedback textual sobre a performance"""
        if rating == "perfect":
            return "Perfeito! Pose idêntica!"

        # Encontrar pontos fracos
        weak_points = []

        # Verificar braços
        arm_score = (kp_scores.get("left_wrist", 0) + kp_scores.get("right_wrist", 0) +
                     kp_scores.get("left_elbow", 0) + kp_scores.get("right_elbow", 0)) / 4
        if arm_score < 0.6:
            weak_points.append("braços")

        # Verificar pernas
        leg_score = (kp_scores.get("left_knee", 0) + kp_scores.get("right_knee", 0) +
                     kp_scores.get("left_ankle", 0) + kp_scores.get("right_ankle", 0)) / 4
        if leg_score < 0.6:
            weak_points.append("pernas")

        # Verificar cotovelos (ângulos)
        elbow_score = (angle_scores.get("left_elbow", 0) + angle_scores.get("right_elbow", 0)) / 2
        if elbow_score < 0.6:
            weak_points.append("cotovelos")

        if weak_points:
            return f"Ajuste: {', '.join(weak_points)}"
        elif rating == "good":
            return "Muito bom! Quase perfeito!"
        elif rating == "ok":
            return "Bom esforço! Continue tentando!"
        else:
            return "Tente novamente!"


def calculate_pose_similarity(pose1: Pose, pose2: Pose) -> float:
    """
    Função helper para calcular similaridade rápida entre duas poses.
    Retorna valor de 0-100.
    """
    comparator = PoseComparator()
    result = comparator.compare(pose1, pose2)
    return result.overall_score
