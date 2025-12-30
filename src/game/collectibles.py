"""
BFF Dance - Sistema de Coletáveis
"""
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum

from ..config.settings import (
    settings, COLLECTIBLES, Theme,
    PLAYER_COLORS
)
from ..core.pose_detector import Pose


@dataclass
class Collectible:
    """Um coletável na tela"""
    name: str
    emoji: str
    points: int
    x: float
    y: float
    spawn_time: float
    collected: bool = False
    collected_by: int = -1  # ID do jogador que coletou
    size: float = 60.0  # Tamanho visual

    @property
    def age(self) -> float:
        """Tempo desde o spawn em segundos"""
        return time.time() - self.spawn_time


class CollectibleManager:
    """Gerenciador de coletáveis na tela"""

    def __init__(self, theme: Theme = Theme.MIXED):
        self.theme = theme
        self.active_collectibles: List[Collectible] = []
        self.collected_items: List[Collectible] = []

        self.grab_radius = settings.gameplay.collectible_grab_radius
        self.max_active = 3  # Máximo de coletáveis simultâneos
        self.lifetime = 12.0  # Segundos antes de desaparecer

        # Intervalo aleatório de spawn (10-30 segundos)
        self.spawn_interval_min = 10.0
        self.spawn_interval_max = 30.0
        self._next_spawn_interval = self._random_interval()
        self._last_spawn_time = 0.0
        # Usar coordenadas da câmera (não do display) pois poses estão nesse espaço
        self._screen_width = settings.camera.width
        self._screen_height = settings.camera.height

        # Margem para não spawnar nas bordas
        self._margin = 80

    def _random_interval(self) -> float:
        """Gera intervalo aleatório para próximo spawn"""
        return random.uniform(self.spawn_interval_min, self.spawn_interval_max)

    def set_theme(self, theme: Theme):
        """Define o tema de coletáveis"""
        self.theme = theme

    def update(self, poses: List[Pose]) -> List[Collectible]:
        """
        Atualiza coletáveis e verifica coletas.

        Args:
            poses: Lista de poses dos jogadores

        Returns:
            Lista de coletáveis que foram coletados neste frame
        """
        current_time = time.time()
        newly_collected = []

        # Spawnar novos coletáveis (intervalo aleatório)
        if (current_time - self._last_spawn_time >= self._next_spawn_interval and
            len(self.active_collectibles) < self.max_active):
            self._spawn_collectible()
            self._last_spawn_time = current_time
            self._next_spawn_interval = self._random_interval()  # Novo intervalo aleatório

        # Verificar coletas e expiração
        remaining = []
        for collectible in self.active_collectibles:
            # Verificar expiração
            if collectible.age > self.lifetime:
                continue

            # Verificar coleta por cada jogador
            collected = False
            for player_id, pose in enumerate(poses):
                if self._check_grab(collectible, pose):
                    collectible.collected = True
                    collectible.collected_by = player_id
                    newly_collected.append(collectible)
                    self.collected_items.append(collectible)
                    collected = True
                    break

            if not collected:
                remaining.append(collectible)

        self.active_collectibles = remaining
        return newly_collected

    def _spawn_collectible(self):
        """Spawna um novo coletável em posição aleatória"""
        items = COLLECTIBLES.get(self.theme, COLLECTIBLES[Theme.MIXED])
        if not items:
            return

        item = random.choice(items)

        # Posição aleatória - SEMPRE nos lados extremos para não sobrepor jogadores
        # Lados da tela (bordas laterais)
        if random.random() < 0.5:
            # Lado esquerdo extremo
            x = random.randint(self._margin, int(self._screen_width * 0.15))
        else:
            # Lado direito extremo
            x = random.randint(int(self._screen_width * 0.85), self._screen_width - self._margin)

        # Altura variada, mais para baixo (area de alcance das maos)
        y = random.randint(int(self._screen_height * 0.3), int(self._screen_height * 0.7))

        collectible = Collectible(
            name=item['name'],
            emoji=item['emoji'],
            points=item['points'],
            x=x,
            y=y,
            spawn_time=time.time()
        )

        self.active_collectibles.append(collectible)

    def _check_grab(self, collectible: Collectible, pose: Pose) -> bool:
        """
        Verifica se um jogador pegou o coletável.

        Verifica proximidade das mãos (pulsos) com o coletável.
        Ambos (coletável e pose) estão em coordenadas de câmera (não espelhadas).
        """
        # Índices dos pulsos no COCO keypoints
        LEFT_WRIST = 9
        RIGHT_WRIST = 10

        for wrist_idx in [LEFT_WRIST, RIGHT_WRIST]:
            if wrist_idx < len(pose.keypoints):
                kp = pose.keypoints[wrist_idx]
                if kp.confidence > 0.3:
                    # Ambos estão em coordenadas de câmera (sem espelhamento)
                    # O espelhamento só acontece na renderização
                    distance = ((collectible.x - kp.x) ** 2 +
                               (collectible.y - kp.y) ** 2) ** 0.5

                    if distance < self.grab_radius:
                        return True

        return False

    def get_player_collectibles_score(self, player_id: int) -> int:
        """Retorna pontuação total de coletáveis de um jogador"""
        return sum(
            c.points for c in self.collected_items
            if c.collected_by == player_id
        )

    def reset(self):
        """Reseta o estado dos coletáveis"""
        self.active_collectibles.clear()
        self.collected_items.clear()
        self._last_spawn_time = 0.0


class EasterEggType(Enum):
    """Tipos de easter eggs"""
    HEART = "heart"
    HIGH_FIVE = "high_five"
    MIRROR = "mirror"


@dataclass
class EasterEgg:
    """Um easter egg detectado"""
    type: EasterEggType
    players: List[int]
    timestamp: float
    bonus_points: int = 50


class EasterEggDetector:
    """Detector de easter eggs colaborativos"""

    def __init__(self):
        self.detected_eggs: List[EasterEgg] = []
        self.heart_distance = settings.gameplay.heart_detection_distance
        self.cooldown = 3.0  # Segundos entre detecções do mesmo tipo
        self._last_detection: Dict[EasterEggType, float] = {}

    def detect(self, poses: List[Pose]) -> Optional[EasterEgg]:
        """
        Detecta easter eggs entre os jogadores.

        Args:
            poses: Lista de poses (precisa de pelo menos 2)

        Returns:
            Easter egg detectado ou None
        """
        if len(poses) < 2:
            return None

        current_time = time.time()

        # Verificar cooldown
        def can_detect(egg_type: EasterEggType) -> bool:
            last = self._last_detection.get(egg_type, 0)
            return current_time - last >= self.cooldown

        # Detectar coração (mãos próximas formando coração)
        if can_detect(EasterEggType.HEART):
            if self._detect_heart(poses[0], poses[1]):
                egg = EasterEgg(
                    type=EasterEggType.HEART,
                    players=[0, 1],
                    timestamp=current_time,
                    bonus_points=50
                )
                self.detected_eggs.append(egg)
                self._last_detection[EasterEggType.HEART] = current_time
                return egg

        # Detectar high-five
        if can_detect(EasterEggType.HIGH_FIVE):
            if self._detect_high_five(poses[0], poses[1]):
                egg = EasterEgg(
                    type=EasterEggType.HIGH_FIVE,
                    players=[0, 1],
                    timestamp=current_time,
                    bonus_points=30
                )
                self.detected_eggs.append(egg)
                self._last_detection[EasterEggType.HIGH_FIVE] = current_time
                return egg

        # Detectar pose espelhada
        if can_detect(EasterEggType.MIRROR):
            if self._detect_mirror(poses[0], poses[1]):
                egg = EasterEgg(
                    type=EasterEggType.MIRROR,
                    players=[0, 1],
                    timestamp=current_time,
                    bonus_points=40
                )
                self.detected_eggs.append(egg)
                self._last_detection[EasterEggType.MIRROR] = current_time
                return egg

        return None

    def _detect_heart(self, pose1: Pose, pose2: Pose) -> bool:
        """
        Detecta gesto de coração entre dois jogadores.
        Os pulsos devem estar próximos e elevados.
        """
        LEFT_WRIST = 9
        RIGHT_WRIST = 10
        NOSE = 0

        # Pegar pulsos de ambos os jogadores
        try:
            # Jogador 1: pulso direito
            wrist1 = pose1.keypoints[RIGHT_WRIST]
            # Jogador 2: pulso esquerdo
            wrist2 = pose2.keypoints[LEFT_WRIST]
            # Narizes para referência de altura
            nose1 = pose1.keypoints[NOSE]
            nose2 = pose2.keypoints[NOSE]
        except (IndexError, AttributeError):
            return False

        # Verificar confiança
        if (wrist1.confidence < 0.5 or wrist2.confidence < 0.5 or
            nose1.confidence < 0.3 or nose2.confidence < 0.3):
            return False

        # Verificar se pulsos estão próximos
        distance = ((wrist1.x - wrist2.x) ** 2 + (wrist1.y - wrist2.y) ** 2) ** 0.5

        if distance > self.heart_distance:
            return False

        # Verificar se estão acima do nível do nariz (braços levantados)
        avg_nose_y = (nose1.y + nose2.y) / 2
        avg_wrist_y = (wrist1.y + wrist2.y) / 2

        # Pulsos devem estar acima (menor Y) ou próximos do nariz
        if avg_wrist_y > avg_nose_y + 50:  # Tolerância
            return False

        return True

    def _detect_high_five(self, pose1: Pose, pose2: Pose) -> bool:
        """
        Detecta high-five entre dois jogadores.
        Mãos devem estar próximas e no meio entre os jogadores.
        """
        LEFT_WRIST = 9
        RIGHT_WRIST = 10

        try:
            # Tentar ambas as combinações de mãos
            combinations = [
                (pose1.keypoints[RIGHT_WRIST], pose2.keypoints[LEFT_WRIST]),
                (pose1.keypoints[LEFT_WRIST], pose2.keypoints[RIGHT_WRIST]),
            ]
        except (IndexError, AttributeError):
            return False

        for wrist1, wrist2 in combinations:
            if wrist1.confidence < 0.5 or wrist2.confidence < 0.5:
                continue

            # Calcular distância
            distance = ((wrist1.x - wrist2.x) ** 2 + (wrist1.y - wrist2.y) ** 2) ** 0.5

            # High-five requer contato mais próximo
            if distance < self.heart_distance * 0.7:
                # Verificar se as mãos estão relativamente altas
                avg_y = (wrist1.y + wrist2.y) / 2
                if avg_y < settings.display.height * 0.6:
                    return True

        return False

    def _detect_mirror(self, pose1: Pose, pose2: Pose) -> bool:
        """
        Detecta poses espelhadas.
        Compara simetria dos keypoints principais.
        """
        # Keypoints a comparar (pares espelhados)
        mirror_pairs = [
            (5, 6),   # Ombros
            (7, 8),   # Cotovelos
            (9, 10),  # Pulsos
            (11, 12), # Quadris
        ]

        try:
            # Calcular centros das poses
            center1_x = pose1.center_x
            center2_x = pose2.center_x

            # Para cada par, verificar se a posição relativa é espelhada
            mirror_score = 0
            valid_pairs = 0

            for left_idx, right_idx in mirror_pairs:
                # Pose 1: pegar ambos os lados
                kp1_left = pose1.keypoints[left_idx]
                kp1_right = pose1.keypoints[right_idx]

                # Pose 2: pegar ambos os lados (espelhados)
                kp2_left = pose2.keypoints[left_idx]
                kp2_right = pose2.keypoints[right_idx]

                if all(kp.confidence > 0.3 for kp in [kp1_left, kp1_right, kp2_left, kp2_right]):
                    # Calcular posição relativa ao centro
                    rel1_left = kp1_left.x - center1_x
                    rel1_right = kp1_right.x - center1_x

                    rel2_left = kp2_left.x - center2_x
                    rel2_right = kp2_right.x - center2_x

                    # Em poses espelhadas:
                    # - O lado esquerdo de um deve corresponder ao direito do outro
                    # Verificar se rel1_left ≈ -rel2_right e rel1_right ≈ -rel2_left
                    diff1 = abs(rel1_left + rel2_right)
                    diff2 = abs(rel1_right + rel2_left)

                    # Normalizar pela largura média das poses
                    width1 = abs(pose1.bbox[2] - pose1.bbox[0])
                    width2 = abs(pose2.bbox[2] - pose2.bbox[0])
                    avg_width = (width1 + width2) / 2

                    if avg_width > 0:
                        norm_diff = (diff1 + diff2) / (2 * avg_width)
                        if norm_diff < 0.3:  # Tolerância de 30%
                            mirror_score += 1
                    valid_pairs += 1

            # Considerar espelhado se maioria dos pares corresponder
            if valid_pairs >= 2 and mirror_score >= valid_pairs * 0.6:
                return True

        except (IndexError, AttributeError, ZeroDivisionError):
            pass

        return False

    def get_message(self, egg_type: EasterEggType) -> str:
        """Retorna mensagem para exibir quando easter egg é detectado"""
        messages = {
            EasterEggType.HEART: "Coração!",
            EasterEggType.HIGH_FIVE: "High Five!",
            EasterEggType.MIRROR: "Espelho!",
        }
        return messages.get(egg_type, "Easter Egg!")

    def reset(self):
        """Reseta o estado do detector"""
        self.detected_eggs.clear()
        self._last_detection.clear()
