"""
BFF Dance - Renderer Pygame
"""
import pygame
import numpy as np
import cv2
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

from ..config.settings import (
    settings, SKELETON_CONNECTIONS, PLAYER_COLORS,
    KEYPOINT_NAMES, FEEDBACK_MESSAGES
)
from ..core.pose_detector import Pose


class GameScreen(Enum):
    """Telas do jogo"""
    MENU = "menu"
    PLAYING = "playing"
    COUNTDOWN = "countdown"
    RESULTS = "results"
    PAUSE = "pause"


@dataclass
class UIMessage:
    """Mensagem temporária na tela"""
    text: str
    color: Tuple[int, int, int]
    duration: float  # segundos
    start_time: float
    size: int = 48
    position: str = "center"  # center, top, bottom


class Renderer:
    """Renderizador principal usando Pygame"""

    def __init__(self):
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.fonts: Dict[str, pygame.font.Font] = {}
        self.width = settings.display.width
        self.height = settings.display.height
        self._initialized = False

        # UI state
        self.messages: List[UIMessage] = []
        self.current_screen = GameScreen.MENU

        # Cache para conversão de frames
        self._frame_surface: Optional[pygame.Surface] = None

    def initialize(self) -> bool:
        """Inicializa Pygame e cria janela"""
        try:
            pygame.init()
            pygame.font.init()

            # Configurar display
            flags = pygame.HWSURFACE | pygame.DOUBLEBUF
            if settings.display.fullscreen:
                flags |= pygame.FULLSCREEN

            self.screen = pygame.display.set_mode(
                (self.width, self.height), flags
            )
            pygame.display.set_caption("BFF Dance")

            # Clock para controle de FPS
            self.clock = pygame.time.Clock()

            # Carregar fontes
            self._load_fonts()

            # Esconder cursor do mouse
            pygame.mouse.set_visible(False)

            self._initialized = True
            print(f"[INFO] Pygame inicializado: {self.width}x{self.height}")
            return True

        except Exception as e:
            print(f"[ERROR] Falha ao inicializar Pygame: {e}")
            return False

    def _load_fonts(self):
        """Carrega fontes do sistema"""
        try:
            # Tentar usar fonte do sistema
            self.fonts = {
                'small': pygame.font.Font(None, 24),
                'medium': pygame.font.Font(None, 36),
                'large': pygame.font.Font(None, 48),
                'xlarge': pygame.font.Font(None, 72),
                'title': pygame.font.Font(None, 96),
            }
        except Exception as e:
            print(f"[WARN] Usando fonte padrão: {e}")
            for name in ['small', 'medium', 'large', 'xlarge', 'title']:
                self.fonts[name] = pygame.font.SysFont('arial', 24)

    def process_events(self) -> List[str]:
        """
        Processa eventos do Pygame.
        Retorna lista de ações: ['quit', 'pause', 'select', 'back', etc.]
        """
        actions = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append('quit')

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    actions.append('back')
                elif event.key == pygame.K_SPACE:
                    actions.append('select')
                elif event.key == pygame.K_p:
                    actions.append('pause')
                elif event.key == pygame.K_q:
                    actions.append('quit')
                elif event.key == pygame.K_RETURN:
                    actions.append('select')
                elif event.key == pygame.K_UP:
                    actions.append('up')
                elif event.key == pygame.K_DOWN:
                    actions.append('down')

        return actions

    def render_frame(
        self,
        frame: np.ndarray,
        poses: List[Pose],
        game_state: Optional[Dict] = None
    ):
        """
        Renderiza um frame completo.

        Args:
            frame: Frame BGR da câmera
            poses: Lista de poses detectadas
            game_state: Estado do jogo (scores, timer, turno, etc.)
        """
        if not self._initialized:
            return

        # Converter frame para surface Pygame
        self._draw_camera_frame(frame)

        # Desenhar esqueletos
        for i, pose in enumerate(poses):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            self._draw_skeleton(pose, color)

        # Desenhar UI do jogo
        if game_state:
            self._draw_game_ui(game_state)

        # Desenhar mensagens temporárias
        self._draw_messages()

        # Atualizar display
        pygame.display.flip()

        # Limitar FPS
        self.clock.tick(settings.display.fps)

    def _draw_camera_frame(self, frame: np.ndarray):
        """Converte e desenha frame da câmera"""
        # Converter BGR para RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Redimensionar se necessário
        if frame_rgb.shape[1] != self.width or frame_rgb.shape[0] != self.height:
            frame_rgb = cv2.resize(frame_rgb, (self.width, self.height))

        # Espelhar horizontalmente (efeito espelho)
        frame_rgb = cv2.flip(frame_rgb, 1)

        # Converter para surface Pygame
        # Pygame espera array (width, height, 3) transposto
        frame_surface = pygame.surfarray.make_surface(
            np.transpose(frame_rgb, (1, 0, 2))
        )

        # Desenhar na tela
        self.screen.blit(frame_surface, (0, 0))

    def _draw_skeleton(self, pose: Pose, color: Tuple[int, int, int]):
        """Desenha esqueleto de uma pose"""
        if not settings.display.show_skeleton:
            return

        keypoints = pose.keypoints

        # Escala do frame da câmera para o display
        # Frame é 1280x720, display é self.width x self.height
        scale_x = self.width / settings.camera.width
        scale_y = self.height / settings.camera.height

        # Ajustar coordenadas: escalar e espelhar
        def transform(x, y):
            # Escalar para tamanho do display
            sx = x * scale_x
            sy = y * scale_y
            # Espelhar horizontalmente
            sx = self.width - sx
            return int(sx), int(sy)

        # Desenhar conexões
        for start_idx, end_idx in SKELETON_CONNECTIONS:
            if start_idx < len(keypoints) and end_idx < len(keypoints):
                kp1 = keypoints[start_idx]
                kp2 = keypoints[end_idx]

                # Verificar confiança mínima
                if kp1.confidence > 0.3 and kp2.confidence > 0.3:
                    x1, y1 = transform(kp1.x, kp1.y)
                    x2, y2 = transform(kp2.x, kp2.y)

                    # Desenhar linha
                    pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), 4)

        # Desenhar keypoints
        if settings.display.show_keypoints:
            for kp in keypoints:
                if kp.confidence > 0.3:
                    x, y = transform(kp.x, kp.y)

                    # Círculo externo (borda)
                    pygame.draw.circle(self.screen, (255, 255, 255), (x, y), 8)
                    # Círculo interno (cor do jogador)
                    pygame.draw.circle(self.screen, color, (x, y), 5)

    def _draw_game_ui(self, game_state: Dict):
        """Desenha elementos de UI do jogo"""
        # Scores dos jogadores
        if 'players' in game_state:
            self._draw_player_scores(game_state['players'])

        # Timer
        if 'timer' in game_state:
            self._draw_timer(game_state['timer'])

        # Indicador de turno
        if 'current_turn' in game_state:
            self._draw_turn_indicator(game_state['current_turn'])

        # Combo
        if 'combo' in game_state and game_state['combo'] > 1:
            self._draw_combo(game_state['combo'])

        # Coletáveis
        if 'collectibles' in game_state:
            self._draw_collectibles(game_state['collectibles'])

        # Instrução atual
        if 'instruction' in game_state:
            self._draw_instruction(game_state['instruction'])

    def _draw_player_scores(self, players: List[Dict]):
        """Desenha scores dos jogadores"""
        for i, player in enumerate(players):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            x = 20 if i == 0 else self.width - 200
            y = 20

            # Nome do jogador
            name_text = self.fonts['medium'].render(
                player.get('name', f'Jogador {i+1}'),
                True, color
            )
            self.screen.blit(name_text, (x, y))

            # Score
            score_text = self.fonts['large'].render(
                str(player.get('score', 0)),
                True, (255, 255, 255)
            )
            self.screen.blit(score_text, (x, y + 30))

    def _draw_timer(self, seconds: float):
        """Desenha timer central"""
        timer_text = self.fonts['xlarge'].render(
            f"{int(seconds)}",
            True, (255, 255, 255)
        )
        rect = timer_text.get_rect(center=(self.width // 2, 50))

        # Fundo semi-transparente
        bg_rect = rect.inflate(20, 10)
        pygame.draw.rect(self.screen, (0, 0, 0, 128), bg_rect, border_radius=10)

        self.screen.blit(timer_text, rect)

    def _draw_turn_indicator(self, current_turn: int):
        """Desenha indicador de quem está no turno"""
        color = PLAYER_COLORS[current_turn % len(PLAYER_COLORS)]

        # Seta ou destaque para o jogador atual
        if current_turn == 0:
            x = 10
        else:
            x = self.width - 30

        # Triângulo indicador
        points = [(x, 80), (x + 20, 90), (x, 100)]
        pygame.draw.polygon(self.screen, color, points)

    def _draw_combo(self, combo: int):
        """Desenha contador de combo"""
        combo_text = self.fonts['large'].render(
            f"Combo x{combo}!",
            True, (255, 215, 0)  # Dourado
        )
        rect = combo_text.get_rect(center=(self.width // 2, 100))
        self.screen.blit(combo_text, rect)

    def _draw_collectibles(self, collectibles: List[Dict]):
        """Desenha coletáveis na tela"""
        for item in collectibles:
            x = int(item.get('x', 0))
            y = int(item.get('y', 0))
            emoji = item.get('emoji', '?')
            age = item.get('age', 0)

            # Animação de entrada (crescer)
            scale = min(1.0, age / 0.3)

            # Animação de pulsação
            import math
            pulse = 1.0 + 0.1 * math.sin(age * 4)
            size = int(40 * scale * pulse)

            # Renderizar emoji como texto
            font = pygame.font.Font(None, size)
            text = font.render(emoji, True, (255, 255, 255))
            rect = text.get_rect(center=(x, y))

            # Brilho ao redor
            glow_color = (255, 255, 100, 100)
            glow_size = size + 10
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surf, glow_color,
                (glow_size, glow_size), glow_size
            )
            glow_rect = glow_surf.get_rect(center=(x, y))
            self.screen.blit(glow_surf, glow_rect)

            # Desenhar emoji
            self.screen.blit(text, rect)

    def _draw_instruction(self, instruction: str):
        """Desenha instrução na parte inferior"""
        text = self.fonts['medium'].render(instruction, True, (255, 255, 255))
        rect = text.get_rect(center=(self.width // 2, self.height - 50))

        # Fundo semi-transparente
        bg_rect = rect.inflate(20, 10)
        s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, bg_rect.topleft)

        self.screen.blit(text, rect)

    def _draw_messages(self):
        """Desenha mensagens temporárias"""
        current_time = pygame.time.get_ticks() / 1000.0

        # Remover mensagens expiradas
        self.messages = [
            msg for msg in self.messages
            if current_time - msg.start_time < msg.duration
        ]

        # Desenhar mensagens ativas
        for msg in self.messages:
            elapsed = current_time - msg.start_time

            # Fade out no final
            alpha = 255
            if elapsed > msg.duration - 0.5:
                alpha = int(255 * (msg.duration - elapsed) / 0.5)

            # Escala de entrada
            scale = min(1.0, elapsed / 0.2)
            font_size = int(msg.size * scale)

            font = pygame.font.Font(None, max(font_size, 12))
            text = font.render(msg.text, True, msg.color)
            text.set_alpha(alpha)

            # Posicionar
            if msg.position == "center":
                rect = text.get_rect(center=(self.width // 2, self.height // 2))
            elif msg.position == "top":
                rect = text.get_rect(center=(self.width // 2, 150))
            else:  # bottom
                rect = text.get_rect(center=(self.width // 2, self.height - 150))

            self.screen.blit(text, rect)

    def show_message(
        self,
        text: str,
        color: Tuple[int, int, int] = (255, 255, 255),
        duration: float = 2.0,
        size: int = 48,
        position: str = "center"
    ):
        """Mostra mensagem temporária na tela"""
        msg = UIMessage(
            text=text,
            color=color,
            duration=duration,
            start_time=pygame.time.get_ticks() / 1000.0,
            size=size,
            position=position
        )
        self.messages.append(msg)

    def show_feedback(self, feedback_type: str):
        """Mostra mensagem de feedback (perfect, good, ok, miss)"""
        import random

        messages = FEEDBACK_MESSAGES.get(feedback_type, [""])
        text = random.choice(messages)

        colors = {
            'perfect': (0, 255, 0),      # Verde
            'good': (0, 200, 255),        # Ciano
            'ok': (255, 255, 0),          # Amarelo
            'miss': (255, 100, 100),      # Vermelho claro
            'easter_egg': (255, 0, 255),  # Magenta
        }

        color = colors.get(feedback_type, (255, 255, 255))
        self.show_message(text, color, duration=1.5, size=72)

    def render_countdown(self, number: int):
        """Renderiza contagem regressiva"""
        self.screen.fill((0, 0, 0))

        text = self.fonts['title'].render(str(number), True, (255, 255, 255))
        rect = text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(text, rect)

        pygame.display.flip()

    def render_menu(self, options: List[str], selected: int, title: str = "BFF Dance"):
        """Renderiza tela de menu"""
        self.screen.fill((30, 30, 50))

        # Título
        title_text = self.fonts['title'].render(title, True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(self.width // 2, 100))
        self.screen.blit(title_text, title_rect)

        # Opções
        start_y = 250
        for i, option in enumerate(options):
            color = (255, 215, 0) if i == selected else (200, 200, 200)
            prefix = "> " if i == selected else "  "

            text = self.fonts['large'].render(prefix + option, True, color)
            rect = text.get_rect(center=(self.width // 2, start_y + i * 60))
            self.screen.blit(text, rect)

        # Instrução
        hint = self.fonts['small'].render(
            "Setas para navegar, ENTER para selecionar, ESC para voltar",
            True, (150, 150, 150)
        )
        hint_rect = hint.get_rect(center=(self.width // 2, self.height - 30))
        self.screen.blit(hint, hint_rect)

        pygame.display.flip()
        self.clock.tick(30)

    def render_results(self, results: Dict):
        """Renderiza tela de resultados"""
        self.screen.fill((30, 30, 50))

        # Título
        title = self.fonts['title'].render("Resultados", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, 80))
        self.screen.blit(title, title_rect)

        # Vencedor
        if 'winner' in results:
            winner_color = PLAYER_COLORS[results['winner'] % len(PLAYER_COLORS)]
            winner_text = self.fonts['xlarge'].render(
                f"Jogador {results['winner'] + 1} venceu!",
                True, winner_color
            )
            winner_rect = winner_text.get_rect(center=(self.width // 2, 180))
            self.screen.blit(winner_text, winner_rect)

        # Scores finais
        if 'players' in results:
            y = 280
            for i, player in enumerate(results['players']):
                color = PLAYER_COLORS[i % len(PLAYER_COLORS)]

                name = player.get('name', f'Jogador {i+1}')
                score = player.get('score', 0)

                text = self.fonts['large'].render(
                    f"{name}: {score} pontos",
                    True, color
                )
                rect = text.get_rect(center=(self.width // 2, y))
                self.screen.blit(text, rect)
                y += 50

        # Instrução
        hint = self.fonts['medium'].render(
            "Pressione ENTER para continuar",
            True, (150, 150, 150)
        )
        hint_rect = hint.get_rect(center=(self.width // 2, self.height - 50))
        self.screen.blit(hint, hint_rect)

        pygame.display.flip()
        self.clock.tick(30)

    def cleanup(self):
        """Limpa recursos do Pygame"""
        if self._initialized:
            pygame.quit()
            self._initialized = False
            print("[INFO] Pygame finalizado")

    @property
    def fps(self) -> float:
        """Retorna FPS atual"""
        if self.clock:
            return self.clock.get_fps()
        return 0.0
