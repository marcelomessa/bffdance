"""
BFF Dance - Botões Tocáveis
Botões na tela que podem ser acionados com as mãos
"""
import pygame
import time
import math
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class TouchButton:
    """Botão que pode ser tocado com a mão"""
    x: int
    y: int
    width: int
    height: int
    label: str
    action: str  # ID da ação
    emoji: str = ""
    color: Tuple[int, int, int] = (100, 100, 150)
    hover_color: Tuple[int, int, int] = (150, 150, 200)
    active_color: Tuple[int, int, int] = (100, 255, 100)

    # Estado
    hover_progress: float = 0.0  # 0-1, tempo de hover
    is_hovered: bool = False
    last_hover_time: float = 0.0
    triggered: bool = False

    # Configuração
    trigger_time: float = 0.8  # Segundos para ativar


class TouchButtonManager:
    """Gerencia botões tocáveis na tela"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_w = screen_width
        self.screen_h = screen_height
        self.buttons: List[TouchButton] = []
        self.scale_x = 1.0
        self.scale_y = 1.0

        # Fonts
        self.font = None
        self.small_font = None

    def set_scale(self, source_width: int, source_height: int):
        """Define escala de conversão das coordenadas da pose"""
        self.scale_x = self.screen_w / source_width
        self.scale_y = self.screen_h / source_height

    def init_fonts(self):
        """Inicializa fontes"""
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)

    def clear(self):
        """Remove todos os botões"""
        self.buttons = []

    def add_button(self, x: int, y: int, width: int, height: int,
                   label: str, action: str, emoji: str = "",
                   color: Tuple[int, int, int] = None) -> TouchButton:
        """Adiciona um botão"""
        btn = TouchButton(
            x=x, y=y, width=width, height=height,
            label=label, action=action, emoji=emoji
        )
        if color:
            btn.color = color
            btn.hover_color = tuple(min(255, c + 50) for c in color)
        self.buttons.append(btn)
        return btn

    def add_menu_buttons(self, options: List[Tuple[str, str, str]]):
        """
        Adiciona botões de menu no topo da tela
        options: [(label, action, emoji), ...]
        """
        self.clear()

        num_buttons = len(options)
        btn_width = 180
        btn_height = 80
        spacing = 30
        total_width = num_buttons * btn_width + (num_buttons - 1) * spacing
        start_x = (self.screen_w - total_width) // 2
        y = 50

        colors = [
            (100, 150, 100),  # Verde
            (150, 100, 150),  # Roxo
            (150, 150, 100),  # Amarelo
            (100, 150, 150),  # Ciano
        ]

        for i, (label, action, emoji) in enumerate(options):
            x = start_x + i * (btn_width + spacing)
            color = colors[i % len(colors)]
            self.add_button(x, y, btn_width, btn_height, label, action, emoji, color)

    def add_corner_button(self, label: str, action: str, emoji: str = "",
                          position: str = "top-left") -> TouchButton:
        """Adiciona botão em um canto da tela"""
        btn_w, btn_h = 120, 60
        margin = 20

        if position == "top-left":
            x, y = margin, margin
        elif position == "top-right":
            x, y = self.screen_w - btn_w - margin, margin
        elif position == "bottom-left":
            x, y = margin, self.screen_h - btn_h - margin
        elif position == "bottom-right":
            x, y = self.screen_w - btn_w - margin, self.screen_h - btn_h - margin
        else:
            x, y = margin, margin

        return self.add_button(x, y, btn_w, btn_h, label, action, emoji, (150, 80, 80))

    def transform_point(self, x: float, y: float, mirror: bool = True) -> Tuple[int, int]:
        """Transforma coordenadas da pose para coordenadas da tela"""
        sx = x * self.scale_x
        sy = y * self.scale_y
        if mirror:
            sx = self.screen_w - sx
        return int(sx), int(sy)

    def get_hand_positions(self, poses) -> List[Tuple[int, int]]:
        """Extrai posições das mãos de todas as poses"""
        hands = []
        for pose in poses:
            if pose is None or len(pose.keypoints) < 11:
                continue
            # Pulso esquerdo (9) e direito (10)
            for idx in [9, 10]:
                kp = pose.keypoints[idx]
                if kp.confidence > 0.3:
                    x, y = self.transform_point(kp.x, kp.y)
                    hands.append((x, y))
        return hands

    def update(self, poses, dt: float = None) -> Optional[str]:
        """
        Atualiza estado dos botões baseado nas posições das mãos.
        Retorna action do botão ativado, ou None.
        """
        if dt is None:
            dt = 1/30  # Assume 30 FPS

        current_time = time.time()
        hands = self.get_hand_positions(poses)
        triggered_action = None

        for btn in self.buttons:
            btn.triggered = False

            # Verificar se alguma mão está sobre o botão
            hovering = False
            for hx, hy in hands:
                if (btn.x <= hx <= btn.x + btn.width and
                    btn.y <= hy <= btn.y + btn.height):
                    hovering = True
                    break

            if hovering:
                if not btn.is_hovered:
                    btn.is_hovered = True
                    btn.last_hover_time = current_time
                    btn.hover_progress = 0.0
                else:
                    # Aumentar progresso
                    btn.hover_progress = min(1.0, (current_time - btn.last_hover_time) / btn.trigger_time)

                    # Verificar se ativou
                    if btn.hover_progress >= 1.0:
                        btn.triggered = True
                        triggered_action = btn.action
                        # Reset para evitar múltiplos triggers
                        btn.hover_progress = 0.0
                        btn.last_hover_time = current_time + 0.5  # Cooldown
            else:
                btn.is_hovered = False
                btn.hover_progress = max(0, btn.hover_progress - dt * 2)  # Decay rápido

        return triggered_action

    def draw(self, screen: pygame.Surface, emoji_renderer=None):
        """Desenha todos os botões"""
        if self.font is None:
            self.init_fonts()

        for btn in self.buttons:
            self._draw_button(screen, btn, emoji_renderer)

    def _draw_button(self, screen: pygame.Surface, btn: TouchButton, emoji_renderer=None):
        """Desenha um botão individual"""
        # Determinar cor baseada no estado
        if btn.hover_progress >= 1.0 or btn.triggered:
            bg_color = btn.active_color
        elif btn.is_hovered:
            # Interpolar entre color e hover_color
            t = btn.hover_progress
            bg_color = tuple(
                int(btn.color[i] + (btn.active_color[i] - btn.color[i]) * t)
                for i in range(3)
            )
        else:
            bg_color = btn.color

        # Efeito de pulso quando hovering
        scale = 1.0
        if btn.is_hovered:
            scale = 1.0 + 0.05 * math.sin(time.time() * 8)

        # Calcular dimensões com escala
        w = int(btn.width * scale)
        h = int(btn.height * scale)
        x = btn.x - (w - btn.width) // 2
        y = btn.y - (h - btn.height) // 2

        # Sombra
        shadow_surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 100), shadow_surf.get_rect(), border_radius=15)
        screen.blit(shadow_surf, (x + 2, y + 2))

        # Fundo
        btn_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, (*bg_color, 220), btn_surf.get_rect(), border_radius=15)

        # Borda (mais grossa quando hovering)
        border_width = 4 if btn.is_hovered else 2
        border_color = (255, 255, 255) if btn.is_hovered else (200, 200, 200)
        pygame.draw.rect(btn_surf, border_color, btn_surf.get_rect(), border_width, border_radius=15)

        screen.blit(btn_surf, (x, y))

        # Barra de progresso circular ao redor
        if btn.hover_progress > 0:
            self._draw_progress_ring(screen, btn, x, y, w, h)

        # Emoji
        emoji_offset = 0
        if btn.emoji and emoji_renderer:
            emoji_size = min(40, h - 20)
            emoji_surf = emoji_renderer.render(btn.emoji, emoji_size)
            emoji_x = x + 10
            emoji_y = y + (h - emoji_size) // 2
            screen.blit(emoji_surf, (emoji_x, emoji_y))
            emoji_offset = emoji_size + 5

        # Texto
        text_color = (255, 255, 255) if btn.is_hovered else (230, 230, 230)
        text = self.font.render(btn.label, True, text_color)
        text_x = x + emoji_offset + (w - emoji_offset - text.get_width()) // 2
        text_y = y + (h - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))

    def _draw_progress_ring(self, screen: pygame.Surface, btn: TouchButton,
                            x: int, y: int, w: int, h: int):
        """Desenha anel de progresso ao redor do botão"""
        if btn.hover_progress <= 0:
            return

        # Desenhar arco de progresso
        center_x = x + w // 2
        center_y = y + h // 2
        radius = max(w, h) // 2 + 8

        # Cor do progresso (verde)
        color = (100, 255, 100)

        # Ângulo de progresso
        start_angle = -math.pi / 2  # Começa do topo
        end_angle = start_angle + 2 * math.pi * btn.hover_progress

        # Desenhar arco usando linhas
        num_segments = int(30 * btn.hover_progress)
        if num_segments > 1:
            points = []
            for i in range(num_segments + 1):
                angle = start_angle + (end_angle - start_angle) * i / num_segments
                px = center_x + radius * math.cos(angle)
                py = center_y + radius * math.sin(angle)
                points.append((px, py))

            if len(points) >= 2:
                pygame.draw.lines(screen, color, False, points, 4)

        # Indicador no final
        end_x = center_x + radius * math.cos(end_angle)
        end_y = center_y + radius * math.sin(end_angle)
        pygame.draw.circle(screen, color, (int(end_x), int(end_y)), 6)

    def draw_hand_cursors(self, screen: pygame.Surface, poses):
        """Desenha cursores nas posições das mãos"""
        hands = self.get_hand_positions(poses)

        for hx, hy in hands:
            # Círculo exterior
            pygame.draw.circle(screen, (255, 255, 255), (hx, hy), 25, 3)
            # Círculo interior
            pygame.draw.circle(screen, (255, 200, 100), (hx, hy), 15)
            # Ponto central
            pygame.draw.circle(screen, (255, 255, 255), (hx, hy), 5)


# Funções de conveniência

def create_menu_manager(screen_w: int, screen_h: int, source_w: int, source_h: int) -> TouchButtonManager:
    """Cria um gerenciador de botões configurado"""
    manager = TouchButtonManager(screen_w, screen_h)
    manager.set_scale(source_w, source_h)
    manager.init_fonts()
    return manager
