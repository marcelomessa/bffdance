"""
BFF Dance - Avatar Renderer
Renderiza avatares estilizados baseados no esqueleto detectado
"""
import pygame
import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from ..config.settings import SKELETON_CONNECTIONS, PLAYER_COLORS, KEYPOINT_NAMES
from ..core.pose_detector import Pose


@dataclass
class AvatarStyle:
    """Estilo visual do avatar"""
    # Cores principais
    body_color: Tuple[int, int, int] = (255, 255, 255)
    outline_color: Tuple[int, int, int] = (0, 0, 0)
    head_color: Tuple[int, int, int] = (255, 220, 180)  # Tom de pele

    # Tamanhos
    head_radius: int = 40
    joint_radius: int = 12
    limb_width: int = 20
    outline_width: int = 3

    # Efeitos
    glow: bool = True
    glow_color: Tuple[int, int, int] = (255, 255, 255)
    glow_radius: int = 5


# Estilos pré-definidos para os jogadores
PLAYER_STYLES = [
    AvatarStyle(
        body_color=(255, 100, 100),      # Vermelho
        head_color=(255, 200, 180),
        glow_color=(255, 150, 150),
    ),
    AvatarStyle(
        body_color=(100, 150, 255),      # Azul
        head_color=(255, 200, 180),
        glow_color=(150, 180, 255),
    ),
]


class AvatarRenderer:
    """Renderiza avatares 2D baseados em esqueletos"""

    def __init__(self, screen_width: int, screen_height: int):
        self.width = screen_width
        self.height = screen_height

        # Escala das coordenadas (pose -> tela)
        self.scale_x = 1.0
        self.scale_y = 1.0

        # Fator de escala adicional para o corpo (1.0 = tamanho normal)
        self.body_scale = 0.85

        # Cache de superfícies para glow
        self._glow_cache: Dict[Tuple, pygame.Surface] = {}

    def set_scale(self, source_width: int, source_height: int):
        """Define escala de conversão das coordenadas"""
        self.scale_x = self.width / source_width
        self.scale_y = self.height / source_height

    def transform_point(self, x: float, y: float, mirror: bool = True) -> Tuple[int, int]:
        """Transforma coordenadas do esqueleto para a tela"""
        sx = x * self.scale_x
        sy = y * self.scale_y
        if mirror:
            sx = self.width - sx

        # Aplicar escala adicional ao redor do centro da tela
        center_x = self.width / 2
        center_y = self.height / 2
        sx = center_x + (sx - center_x) * self.body_scale
        sy = center_y + (sy - center_y) * self.body_scale

        return int(sx), int(sy)

    def render(
        self,
        screen: pygame.Surface,
        poses: List[Pose],
        styles: Optional[List[AvatarStyle]] = None
    ):
        """
        Renderiza avatares para todas as poses detectadas.

        Args:
            screen: Superfície Pygame para desenhar
            poses: Lista de poses detectadas
            styles: Estilos opcionais por jogador
        """
        if styles is None:
            styles = PLAYER_STYLES

        for i, pose in enumerate(poses):
            style = styles[i % len(styles)]
            self._render_avatar(screen, pose, style)

    def _render_avatar(
        self,
        screen: pygame.Surface,
        pose: Pose,
        style: AvatarStyle
    ):
        """Renderiza um único avatar"""
        keypoints = pose.keypoints

        # Precisamos de keypoints válidos
        if len(keypoints) < 17:
            return

        # Extrair pontos transformados
        points = {}
        for i, kp in enumerate(keypoints):
            if kp.confidence > 0.3:
                points[i] = self.transform_point(kp.x, kp.y)

        # Desenhar corpo (de trás para frente)
        self._draw_body(screen, points, style)
        self._draw_head(screen, points, style)

    def _draw_body(
        self,
        screen: pygame.Surface,
        points: Dict[int, Tuple[int, int]],
        style: AvatarStyle
    ):
        """Desenha o corpo do avatar"""
        # Definir grupos de membros com cores
        limb_groups = [
            # Tronco
            [(5, 6), (5, 11), (6, 12), (11, 12)],
            # Braço esquerdo
            [(5, 7), (7, 9)],
            # Braço direito
            [(6, 8), (8, 10)],
            # Perna esquerda
            [(11, 13), (13, 15)],
            # Perna direita
            [(12, 14), (14, 16)],
        ]

        # Desenhar cada membro
        for connections in limb_groups:
            for start_idx, end_idx in connections:
                if start_idx in points and end_idx in points:
                    p1 = points[start_idx]
                    p2 = points[end_idx]

                    # Glow (opcional)
                    if style.glow:
                        pygame.draw.line(
                            screen, style.glow_color,
                            p1, p2, style.limb_width + style.glow_radius * 2
                        )

                    # Outline
                    pygame.draw.line(
                        screen, style.outline_color,
                        p1, p2, style.limb_width + style.outline_width * 2
                    )

                    # Membro
                    pygame.draw.line(
                        screen, style.body_color,
                        p1, p2, style.limb_width
                    )

        # Desenhar articulações
        joint_indices = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        for idx in joint_indices:
            if idx in points:
                p = points[idx]

                # Glow
                if style.glow:
                    pygame.draw.circle(
                        screen, style.glow_color,
                        p, style.joint_radius + style.glow_radius
                    )

                # Outline
                pygame.draw.circle(
                    screen, style.outline_color,
                    p, style.joint_radius + style.outline_width
                )

                # Articulação
                pygame.draw.circle(
                    screen, style.body_color,
                    p, style.joint_radius
                )

    def _draw_head(
        self,
        screen: pygame.Surface,
        points: Dict[int, Tuple[int, int]],
        style: AvatarStyle
    ):
        """Desenha a cabeça do avatar"""
        # Usar nariz como centro da cabeça, ou média dos olhos
        head_pos = None

        if 0 in points:  # Nariz
            head_pos = points[0]
        elif 1 in points and 2 in points:  # Média dos olhos
            head_pos = (
                (points[1][0] + points[2][0]) // 2,
                (points[1][1] + points[2][1]) // 2
            )

        if head_pos is None:
            return

        # Calcular tamanho da cabeça baseado na distância dos ombros
        head_radius = style.head_radius
        if 5 in points and 6 in points:
            shoulder_dist = math.sqrt(
                (points[5][0] - points[6][0]) ** 2 +
                (points[5][1] - points[6][1]) ** 2
            )
            head_radius = int(shoulder_dist * 0.4)
            head_radius = max(20, min(head_radius, 80))  # Limitar tamanho

        # Glow
        if style.glow:
            pygame.draw.circle(
                screen, style.glow_color,
                head_pos, head_radius + style.glow_radius
            )

        # Outline
        pygame.draw.circle(
            screen, style.outline_color,
            head_pos, head_radius + style.outline_width
        )

        # Cabeça
        pygame.draw.circle(
            screen, style.head_color,
            head_pos, head_radius
        )

        # Olhos simples
        eye_offset_x = head_radius // 3
        eye_offset_y = head_radius // 6
        eye_radius = max(3, head_radius // 8)

        # Olho esquerdo (na perspectiva do avatar, direito na tela espelhada)
        pygame.draw.circle(
            screen, style.outline_color,
            (head_pos[0] - eye_offset_x, head_pos[1] - eye_offset_y),
            eye_radius
        )
        # Olho direito
        pygame.draw.circle(
            screen, style.outline_color,
            (head_pos[0] + eye_offset_x, head_pos[1] - eye_offset_y),
            eye_radius
        )

        # Sorriso
        smile_rect = pygame.Rect(
            head_pos[0] - head_radius // 3,
            head_pos[1],
            head_radius // 1.5,
            head_radius // 3
        )
        pygame.draw.arc(
            screen, style.outline_color,
            smile_rect, 3.14, 2 * 3.14, 2
        )


def draw_gradient_background(
    screen: pygame.Surface,
    color_top: Tuple[int, int, int] = (30, 30, 80),
    color_bottom: Tuple[int, int, int] = (80, 30, 80)
):
    """Desenha um fundo gradiente"""
    width, height = screen.get_size()

    for y in range(height):
        ratio = y / height
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        pygame.draw.line(screen, (r, g, b), (0, y), (width, y))


def draw_disco_floor(
    screen: pygame.Surface,
    time_offset: float = 0,
    tile_size: int = 80
):
    """Desenha um piso de discoteca animado"""
    width, height = screen.get_size()
    floor_y = int(height * 0.7)  # Piso começa em 70% da tela

    colors = [
        (255, 50, 50),   # Vermelho
        (50, 255, 50),   # Verde
        (50, 50, 255),   # Azul
        (255, 255, 50),  # Amarelo
        (255, 50, 255),  # Magenta
        (50, 255, 255),  # Ciano
    ]

    for y in range(floor_y, height, tile_size):
        for x in range(0, width, tile_size):
            # Selecionar cor baseado na posição e tempo
            color_idx = int((x // tile_size + y // tile_size + time_offset) % len(colors))
            color = colors[color_idx]

            # Escurecer baseado na "distância"
            depth = (y - floor_y) / (height - floor_y)
            factor = 0.3 + 0.7 * (1 - depth)
            dark_color = (
                int(color[0] * factor),
                int(color[1] * factor),
                int(color[2] * factor)
            )

            pygame.draw.rect(screen, dark_color, (x, y, tile_size - 2, tile_size - 2))
