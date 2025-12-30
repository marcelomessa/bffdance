#!/usr/bin/env python3
"""
BFF Dance - Demo Completo
Com tela de setup, avatares com emoji e corpo preenchido
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')

os.environ['SDL_VIDEODRIVER'] = 'x11'

import pygame
import time
import math
import random
from src.core.pose_detector import PoseDetector, CameraCapture
from src.core.kinect_capture import KinectCapture
from src.graphics.avatar import draw_gradient_background, draw_disco_floor
from src.audio.audio_manager import AudioManager
from src.game.collectibles import CollectibleManager, EasterEggDetector
from src.config.settings import settings, Theme, SKELETON_CONNECTIONS


# Emojis disponiveis para escolher como rosto
AVATAR_EMOJIS = [
    ("🐼", "Panda"),
    ("🐱", "Gato"),
    ("🐶", "Cachorro"),
    ("🦊", "Raposa"),
    ("🐰", "Coelho"),
    ("🦁", "Leao"),
    ("🐸", "Sapo"),
    ("💀", "Caveira"),
    ("👽", "ET"),
    ("🤖", "Robo"),
    ("🎃", "Abobora"),
    ("⭐", "Estrela"),
]


class EmojiRenderer:
    """Renderiza emojis usando fonte Noto Color Emoji com cache"""

    def __init__(self):
        self.font_path = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
        self.fonts = {}
        self.cache = {}  # Cache de emojis renderizados
        self._load_fonts()

    def _load_fonts(self):
        """Carrega fontes em varios tamanhos"""
        sizes = [24, 32, 48, 64, 80, 96, 128]
        for size in sizes:
            try:
                self.fonts[size] = pygame.font.Font(self.font_path, size)
            except:
                self.fonts[size] = pygame.font.Font(None, size)

    def render(self, emoji: str, size: int = 48) -> pygame.Surface:
        """Renderiza um emoji (com cache)"""
        cache_key = (emoji, size)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Encontrar tamanho mais proximo
        available = sorted(self.fonts.keys())
        best_size = min(available, key=lambda x: abs(x - size))
        font = self.fonts[best_size]

        try:
            surf = font.render(emoji, True, (255, 255, 255))
            # Escalar se necessario
            if best_size != size:
                scale = size / best_size
                new_w = int(surf.get_width() * scale)
                new_h = int(surf.get_height() * scale)
                surf = pygame.transform.scale(surf, (new_w, new_h))
            self.cache[cache_key] = surf
            return surf
        except:
            # Fallback: desenhar circulo colorido
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 200, 100), (size // 2, size // 2), size // 2)
            self.cache[cache_key] = surf
            return surf


class EnhancedAvatarRenderer:
    """Renderiza avatares com corpo preenchido e emoji no rosto"""

    def __init__(self, screen_width: int, screen_height: int, emoji_renderer: EmojiRenderer):
        self.width = screen_width
        self.height = screen_height
        self.emoji_renderer = emoji_renderer
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.body_scale = 0.85

    def set_scale(self, source_width: int, source_height: int):
        self.scale_x = self.width / source_width
        self.scale_y = self.height / source_height

    def transform_point(self, x: float, y: float, mirror: bool = True):
        sx = x * self.scale_x
        sy = y * self.scale_y
        if mirror:
            sx = self.width - sx
        center_x = self.width / 2
        center_y = self.height / 2
        sx = center_x + (sx - center_x) * self.body_scale
        sy = center_y + (sy - center_y) * self.body_scale
        return int(sx), int(sy)

    def render(self, screen, pose, color, emoji):
        """Renderiza um avatar completo"""
        if pose is None or len(pose.keypoints) < 17:
            return

        # Extrair pontos
        points = {}
        for i, kp in enumerate(pose.keypoints):
            if kp.confidence > 0.3:
                points[i] = self.transform_point(kp.x, kp.y)

        # Cores
        body_color = color
        outline_color = tuple(max(0, c - 80) for c in color)
        skin_color = (255, 220, 200)

        # Desenhar corpo preenchido
        self._draw_filled_body(screen, points, body_color, outline_color)

        # Desenhar maos
        self._draw_hands(screen, points, skin_color, outline_color)

        # Desenhar cabeca com emoji
        self._draw_emoji_head(screen, points, emoji, body_color)

    def _draw_filled_body(self, screen, points, body_color, outline_color):
        """Desenha corpo preenchido (torso e membros)"""
        # Torso (poligono)
        torso_indices = [5, 6, 12, 11]  # Ombros e quadris
        torso_points = [points[i] for i in torso_indices if i in points]
        if len(torso_points) >= 3:
            pygame.draw.polygon(screen, body_color, torso_points)
            pygame.draw.polygon(screen, outline_color, torso_points, 4)

        # Membros como capsulas/retangulos arredondados
        limb_connections = [
            (5, 7), (7, 9),    # Braco esquerdo
            (6, 8), (8, 10),   # Braco direito
            (11, 13), (13, 15), # Perna esquerda
            (12, 14), (14, 16), # Perna direita
        ]

        limb_width = 25

        for start_idx, end_idx in limb_connections:
            if start_idx in points and end_idx in points:
                p1 = points[start_idx]
                p2 = points[end_idx]

                # Outline
                pygame.draw.line(screen, outline_color, p1, p2, limb_width + 6)
                # Corpo
                pygame.draw.line(screen, body_color, p1, p2, limb_width)

                # Circulos nas juntas
                pygame.draw.circle(screen, body_color, p1, limb_width // 2 + 2)
                pygame.draw.circle(screen, body_color, p2, limb_width // 2 + 2)

    def _draw_hands(self, screen, points, skin_color, outline_color):
        """Desenha maos estilizadas"""
        hand_indices = [9, 10]  # Pulsos

        for idx in hand_indices:
            if idx in points:
                x, y = points[idx]
                hand_size = 20

                # Palma
                pygame.draw.circle(screen, outline_color, (x, y), hand_size + 3)
                pygame.draw.circle(screen, skin_color, (x, y), hand_size)

                # Dedos simplificados (5 circulos pequenos)
                for i in range(5):
                    angle = math.pi / 2 + (i - 2) * 0.4
                    dx = int(math.cos(angle) * (hand_size + 8))
                    dy = int(-math.sin(angle) * (hand_size + 8))
                    pygame.draw.circle(screen, outline_color, (x + dx, y + dy), 7)
                    pygame.draw.circle(screen, skin_color, (x + dx, y + dy), 5)

    def _draw_emoji_head(self, screen, points, emoji, body_color):
        """Desenha cabeca com emoji"""
        # Calcular tamanho baseado nos ombros
        head_size = 60
        if 5 in points and 6 in points:
            shoulder_dist = math.sqrt(
                (points[5][0] - points[6][0]) ** 2 +
                (points[5][1] - points[6][1]) ** 2
            )
            head_size = int(shoulder_dist * 0.5)
            head_size = max(40, min(head_size, 100))

        # Posicao da cabeca - usar centro dos ombros e subir um pouco
        head_pos = None
        if 5 in points and 6 in points:
            # Centro dos ombros, subindo pela distancia da cabeca
            center_x = (points[5][0] + points[6][0]) // 2
            center_y = (points[5][1] + points[6][1]) // 2
            head_pos = (center_x, center_y - int(head_size * 1.1))
        elif 0 in points:
            head_pos = points[0]

        if head_pos is None:
            return

        # Pescoco conectando ao corpo
        if 5 in points and 6 in points:
            neck_base = ((points[5][0] + points[6][0]) // 2,
                         (points[5][1] + points[6][1]) // 2)
            pygame.draw.line(screen, body_color, neck_base, head_pos, 20)

        # Fundo colorido para a cabeca
        pygame.draw.circle(screen, body_color, head_pos, head_size + 5)
        pygame.draw.circle(screen, (255, 255, 255), head_pos, head_size)

        # Renderizar emoji
        emoji_surf = self.emoji_renderer.render(emoji, head_size * 2)
        emoji_rect = emoji_surf.get_rect(center=head_pos)
        screen.blit(emoji_surf, emoji_rect)


class ParticleSystem:
    """Sistema de particulas simplificado"""

    def __init__(self, max_particles=50):
        self.particles = []
        self.max_particles = max_particles

    def emit(self, x, y, count=5, color=(255, 255, 100)):
        # Limitar total de particulas
        if len(self.particles) >= self.max_particles:
            return
        count = min(count, self.max_particles - len(self.particles))
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 120)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': 1.0,
                'color': color,
                'size': random.randint(4, 10)
            })

    def emit_stars(self, x, y, count=2):
        if len(self.particles) >= self.max_particles:
            return
        count = min(count, self.max_particles - len(self.particles))
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
            speed = random.uniform(80, 140)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': 1.2,
                'color': (255, 215, 0),
                'size': random.randint(8, 14),
                'star': True
            })

    def update(self, dt):
        remaining = []
        for p in self.particles:
            p['life'] -= dt
            if p['life'] > 0:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += 100 * dt  # Gravidade
                remaining.append(p)
        self.particles = remaining

    def draw(self, screen):
        for p in self.particles:
            alpha = max(0, min(255, int(255 * p['life'])))
            size = int(p['size'] * p['life'])
            if size > 1:
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                # Garantir que cor é tupla de inteiros válidos
                r = max(0, min(255, int(p['color'][0])))
                g = max(0, min(255, int(p['color'][1])))
                b = max(0, min(255, int(p['color'][2])))
                color = (r, g, b, alpha)
                if p.get('star'):
                    self._draw_star(surf, size, size, max(2, size), color)
                else:
                    pygame.draw.circle(surf, color, (size, size), size)
                screen.blit(surf, (int(p['x']) - size, int(p['y']) - size))

    def _draw_star(self, surf, cx, cy, size, color):
        points = []
        for i in range(5):
            angle = -math.pi / 2 + i * 2 * math.pi / 5
            points.append((int(cx + size * math.cos(angle)), int(cy + size * math.sin(angle))))
            angle += math.pi / 5
            points.append((int(cx + size * 0.4 * math.cos(angle)), int(cy + size * 0.4 * math.sin(angle))))
        if len(points) >= 3:
            pygame.draw.polygon(surf, color, points)


def draw_stars_rating(screen, score, x, y, max_stars=5, size=30):
    """Desenha estrelas de rating"""
    pts_per_star = 50
    filled = min(max_stars, score // pts_per_star)

    for i in range(max_stars):
        sx = x + i * (size + 8)
        color = (255, 215, 0) if i < filled else (80, 80, 80)
        draw_star_shape(screen, sx, y, size // 2, color)


def draw_star_shape(screen, x, y, size, color):
    """Desenha uma estrela"""
    points = []
    for i in range(5):
        angle = -math.pi / 2 + i * 2 * math.pi / 5
        points.append((x + size * math.cos(angle), y + size * math.sin(angle)))
        angle += math.pi / 5
        points.append((x + size * 0.4 * math.cos(angle), y + size * 0.4 * math.sin(angle)))
    pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, (50, 50, 50), points, 2)


def setup_screen(screen, screen_w, screen_h, detector, camera, emoji_renderer):
    """Tela de setup para escolher avatares"""
    clock = pygame.time.Clock()

    # Fontes
    font_title = pygame.font.Font(None, 80)
    font_medium = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 36)

    # Estado
    players = [None, None]  # [{'emoji_idx': ..., 'center_x': ..., 'pose': ..., 'confirmed': ...}, ...]
    selected_emojis = [0, 6]  # Indices iniciais diferentes
    player_names = ["Jogador 1", "Jogador 2"]
    setup_complete = False

    # Background
    background = pygame.Surface((screen_w, screen_h))
    draw_gradient_background(background, (30, 30, 70), (70, 30, 70))

    # Avatar renderer para preview
    preview_renderer = EnhancedAvatarRenderer(screen_w, screen_h, emoji_renderer)
    preview_renderer.set_scale(settings.camera.width, settings.camera.height)

    print("\n=== SETUP ===")
    print("Entre na frente da camera!")
    print("Levante a MAO DIREITA para proximo emoji")
    print("Levante a MAO ESQUERDA para emoji anterior")
    print("Levante DUAS MAOS BEM ALTO por 2 segundos para confirmar!")

    # Tracking
    last_hand_action = [0, 0]  # Tempo da ultima acao
    ACTION_COOLDOWN = 1.0  # Segundos entre acoes de troca
    both_hands_start = [0, 0]  # Quando comecou a levantar duas maos
    first_confirm_time = None  # Quando primeiro jogador confirmou
    WAIT_FOR_SECOND = 5.0  # Segundos para esperar segundo jogador
    both_hands_last_seen = [0, 0]  # Ultima vez que viu duas maos
    CONFIRM_TIME = 2.0  # Segundos com duas maos para confirmar
    GRACE_PERIOD = 0.3  # Tolerancia para falhas de deteccao

    running = True
    while running and not setup_complete:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # Confirmar e iniciar jogo!
                    # Marcar todos os jogadores detectados como confirmados
                    any_player = False
                    for pid in [0, 1]:
                        if players[pid] is not None:
                            players[pid]['confirmed'] = True
                            any_player = True
                    if any_player:
                        setup_complete = True
                        print("SETUP COMPLETO! Iniciando jogo...")
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if players[0] is not None:
                        players[0]['emoji_idx'] = (players[0]['emoji_idx'] - 1) % len(AVATAR_EMOJIS)
                    else:
                        selected_emojis[0] = (selected_emojis[0] - 1) % len(AVATAR_EMOJIS)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if players[0] is not None:
                        players[0]['emoji_idx'] = (players[0]['emoji_idx'] + 1) % len(AVATAR_EMOJIS)
                    else:
                        selected_emojis[0] = (selected_emojis[0] + 1) % len(AVATAR_EMOJIS)

        current_time = time.time()

        # Capturar e detectar
        ret, frame = camera.read()
        if ret:
            poses = detector.detect(frame)

            # Associar poses a jogadores (por posicao X - esquerda/direita)
            # Resetar poses atuais
            for pid in [0, 1]:
                if players[pid] is not None:
                    players[pid]['pose'] = None

            # Associar poses a jogadores por proximidade (tracking)
            # Primeiro, tentar match com jogadores existentes
            used_poses = set()
            for pid in [0, 1]:
                if players[pid] is not None:
                    best_pose = None
                    best_dist = 200  # Threshold de tracking
                    for pose in poses:
                        if id(pose) in used_poses:
                            continue
                        dist = abs(pose.center_x - players[pid]['center_x'])
                        if dist < best_dist:
                            best_dist = dist
                            best_pose = pose
                    if best_pose:
                        players[pid]['pose'] = best_pose
                        players[pid]['center_x'] = best_pose.center_x
                        used_poses.add(id(best_pose))
                    else:
                        players[pid]['pose'] = None

            # Depois, adicionar novas pessoas como novos jogadores
            for pose in poses:
                if id(pose) in used_poses:
                    continue
                # Encontrar slot vazio
                for pid in [0, 1]:
                    if players[pid] is None:
                        players[pid] = {
                            'center_x': pose.center_x,
                            'emoji_idx': selected_emojis[pid],
                            'pose': pose,
                            'confirmed': False
                        }
                        used_poses.add(id(pose))
                        print(f"Jogador {pid + 1} detectado!")
                        break

            # Verificar gestos de cada jogador
            for pid in [0, 1]:
                if players[pid] is not None and players[pid]['pose'] is not None:
                    pose = players[pid]['pose']

                    if not players[pid]['confirmed']:
                        # Verificar qual mao esta levantada
                        left_up, right_up = get_raised_hands(pose)

                        if left_up and right_up:
                            # DUAS MAOS = confirmar (manter por CONFIRM_TIME segundos)
                            both_hands_last_seen[pid] = current_time
                            if both_hands_start[pid] == 0:
                                both_hands_start[pid] = current_time
                                print(f"Jogador {pid + 1}: segurando duas maos...")
                            elif current_time - both_hands_start[pid] >= CONFIRM_TIME:
                                players[pid]['confirmed'] = True
                                print(f"Jogador {pid + 1}: CONFIRMADO!")
                                both_hands_start[pid] = 0
                        else:
                            # Verificar se esta no periodo de graca
                            if both_hands_start[pid] != 0:
                                time_since_seen = current_time - both_hands_last_seen[pid]
                                if time_since_seen > GRACE_PERIOD:
                                    # Periodo de graca expirou, resetar
                                    both_hands_start[pid] = 0
                                # Senao, manter o progresso

                            # UMA mao = trocar emoji (com cooldown, e nao durante confirmacao)
                            if both_hands_start[pid] == 0 and current_time - last_hand_action[pid] > ACTION_COOLDOWN:
                                if right_up and not left_up:
                                    players[pid]['emoji_idx'] = (players[pid]['emoji_idx'] + 1) % len(AVATAR_EMOJIS)
                                    last_hand_action[pid] = current_time
                                    print(f"Jogador {pid + 1}: proximo emoji -> {AVATAR_EMOJIS[players[pid]['emoji_idx']][1]}")
                                elif left_up and not right_up:
                                    players[pid]['emoji_idx'] = (players[pid]['emoji_idx'] - 1) % len(AVATAR_EMOJIS)
                                    last_hand_action[pid] = current_time
                                    print(f"Jogador {pid + 1}: emoji anterior -> {AVATAR_EMOJIS[players[pid]['emoji_idx']][1]}")

            # Verificar se setup completo (pelo menos 1 jogador confirmado)
            confirmed_players = [p for p in players if p is not None and p['confirmed']]
            if len(confirmed_players) >= 1:
                if len(confirmed_players) == 2:
                    # 2 confirmados - iniciar imediatamente
                    setup_complete = True
                    print("2 jogadores confirmados!")
                else:
                    # 1 confirmado - iniciar timer ou iniciar se timeout
                    if first_confirm_time is None:
                        first_confirm_time = current_time
                        print(f"1 jogador confirmado! Esperando {WAIT_FOR_SECOND}s pelo segundo...")
                    elif current_time - first_confirm_time >= WAIT_FOR_SECOND:
                        # Timeout - iniciar com 1 jogador
                        setup_complete = True
                        print("Timeout! Iniciando com 1 jogador.")

        # === RENDERIZACAO ===
        screen.blit(background, (0, 0))

        # Desenhar avatares em tempo real (area central)
        for pid in [0, 1]:
            if players[pid] is not None and players[pid]['pose'] is not None:
                emoji_idx = players[pid]['emoji_idx']
                emoji = AVATAR_EMOJIS[emoji_idx][0]
                color = (255, 100, 150) if pid == 0 else (100, 150, 255)
                preview_renderer.render(screen, players[pid]['pose'], color, emoji)

        # Titulo
        title = font_title.render("BFF Dance - Setup", True, (255, 255, 255))
        title_rect = title.get_rect(center=(screen_w // 2, 50))
        # Fundo para titulo
        bg = pygame.Surface((title_rect.width + 40, title_rect.height + 20), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 180), bg.get_rect(), border_radius=15)
        screen.blit(bg, (title_rect.x - 20, title_rect.y - 10))
        screen.blit(title, title_rect)

        # Instrucoes
        instructions = [
            "Mao DIREITA levantada = Proximo emoji",
            "Mao ESQUERDA levantada = Emoji anterior",
            "DUAS MAOS levantadas por 2 segundos = CONFIRMAR!"
        ]
        for i, inst in enumerate(instructions):
            text = font_small.render(inst, True, (220, 220, 220))
            rect = text.get_rect(center=(screen_w // 2, 100 + i * 28))
            screen.blit(text, rect)

        # Paineis dos jogadores (compactos no topo)
        panel_w = 300
        panel_h = 250
        panel_y = 180

        for pid in [0, 1]:
            panel_x = 50 if pid == 0 else screen_w - panel_w - 50
            color = (255, 100, 150) if pid == 0 else (100, 150, 255)

            # Fundo do painel semi-transparente
            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            pygame.draw.rect(panel_surf, (30, 30, 50, 200), panel_surf.get_rect(), border_radius=15)
            pygame.draw.rect(panel_surf, color, panel_surf.get_rect(), 3, border_radius=15)
            screen.blit(panel_surf, (panel_x, panel_y))

            # Nome do jogador
            name = f"Jogador {pid + 1}"
            name_text = font_medium.render(name, True, color)
            screen.blit(name_text, name_text.get_rect(center=(panel_x + panel_w // 2, panel_y + 30)))

            # Emoji atual
            if players[pid] is not None:
                emoji_idx = players[pid]['emoji_idx']
            else:
                emoji_idx = selected_emojis[pid]

            emoji, emoji_name = AVATAR_EMOJIS[emoji_idx]
            emoji_surf = emoji_renderer.render(emoji, 70)
            emoji_rect = emoji_surf.get_rect(center=(panel_x + panel_w // 2, panel_y + 90))
            screen.blit(emoji_surf, emoji_rect)

            # Nome do emoji (abaixo do emoji)
            ename_text = font_small.render(emoji_name, True, (200, 200, 200))
            screen.blit(ename_text, ename_text.get_rect(center=(panel_x + panel_w // 2, panel_y + 170)))

            # Status
            if players[pid] is None:
                status = "Entre no seu lado!"
                status_color = (150, 150, 150)
            elif not players[pid]['confirmed']:
                # Mostrar qual gesto fazer
                left_up, right_up = False, False
                if players[pid]['pose'] is not None:
                    left_up, right_up = get_raised_hands(players[pid]['pose'])

                if both_hands_start[pid] > 0:
                    elapsed = current_time - both_hands_start[pid]
                    remaining = max(0, CONFIRM_TIME - elapsed)
                    status = f"Segure! {remaining:.1f}s"
                    status_color = (100, 255, 100)
                elif left_up or right_up:
                    status = "Trocando emoji..."
                    status_color = (255, 255, 100)
                else:
                    status = "Levante as maos!"
                    status_color = (255, 200, 100)
            else:
                status = "PRONTO!"
                status_color = (100, 255, 100)

            status_text = font_small.render(status, True, status_color)
            screen.blit(status_text, status_text.get_rect(center=(panel_x + panel_w // 2, panel_y + 205)))

            # Barra de progresso de confirmacao (duas maos)
            if players[pid] is not None and not players[pid]['confirmed'] and both_hands_start[pid] > 0:
                elapsed = current_time - both_hands_start[pid]
                progress = min(1.0, elapsed / CONFIRM_TIME)
                bar_w = panel_w - 40
                bar_h = 12
                bar_x = panel_x + 20
                bar_y = panel_y + panel_h - 20
                pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
                pygame.draw.rect(screen, (100, 255, 100), (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=6)

        # Contador de jogadores prontos
        ready_count = sum(1 for p in players if p is not None and p['confirmed'])
        total_detected = sum(1 for p in players if p is not None)

        if ready_count == 2:
            ready_text = font_medium.render("TODOS PRONTOS! Iniciando...", True, (100, 255, 100))
        elif ready_count == 1 and first_confirm_time is not None:
            # Countdown para iniciar com 1 jogador
            remaining = max(0, WAIT_FOR_SECOND - (current_time - first_confirm_time))
            ready_text = font_medium.render(f"Iniciando em {remaining:.0f}s... (ou espere 2o jogador)", True, (255, 200, 100))
        elif total_detected == 0:
            ready_text = font_medium.render("Aguardando jogadores...", True, (200, 200, 200))
        else:
            ready_text = font_medium.render(f"Prontos: {ready_count}/{total_detected}", True, (255, 255, 100))
        screen.blit(ready_text, ready_text.get_rect(center=(screen_w // 2, screen_h - 50)))

        pygame.display.flip()
        clock.tick(30)

    # Retornar configuracao APENAS dos jogadores confirmados
    result = []
    for pid in [0, 1]:
        if players[pid] is not None and players[pid].get('confirmed'):
            emoji_idx = players[pid]['emoji_idx']
            initial_x = players[pid].get('center_x')
            result.append({
                'pid': pid,  # ID original para tracking
                'name': player_names[pid],
                'emoji': AVATAR_EMOJIS[emoji_idx][0],
                'emoji_name': AVATAR_EMOJIS[emoji_idx][1],
                'color': (255, 100, 150) if pid == 0 else (100, 150, 255),
                'initial_x': initial_x
            })

    return result


def is_hand_raised(pose):
    """Verifica se a mao esta levantada (acima do ombro)"""
    left_up, right_up = get_raised_hands(pose)
    return left_up or right_up


def get_raised_hands(pose):
    """Retorna (left_raised, right_raised) - mais tolerante"""
    if len(pose.keypoints) < 11:
        return False, False

    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    NOSE = 0

    left_up = False
    right_up = False

    # Referencia: altura do nariz ou ombro
    nose = pose.keypoints[NOSE]
    ref_y = nose.y if nose.confidence > 0.3 else None

    # Mao esquerda - basta estar acima do cotovelo OU perto do nariz
    left_wrist = pose.keypoints[LEFT_WRIST]
    left_elbow = pose.keypoints[LEFT_ELBOW]
    left_shoulder = pose.keypoints[LEFT_SHOULDER]

    if left_wrist.confidence > 0.25:
        # Acima do cotovelo
        if left_elbow.confidence > 0.25 and left_wrist.y < left_elbow.y:
            left_up = True
        # Ou acima do ombro
        elif left_shoulder.confidence > 0.25 and left_wrist.y < left_shoulder.y + 20:
            left_up = True

    # Mao direita
    right_wrist = pose.keypoints[RIGHT_WRIST]
    right_elbow = pose.keypoints[RIGHT_ELBOW]
    right_shoulder = pose.keypoints[RIGHT_SHOULDER]

    if right_wrist.confidence > 0.25:
        # Acima do cotovelo
        if right_elbow.confidence > 0.25 and right_wrist.y < right_elbow.y:
            right_up = True
        # Ou acima do ombro
        elif right_shoulder.confidence > 0.25 and right_wrist.y < right_shoulder.y + 20:
            right_up = True

    return left_up, right_up


def main():
    print("=== BFF Dance - Completo ===")

    pygame.init()
    pygame.font.init()
    # Buffer muito maior para evitar falhas de audio
    pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=8192)

    # Display
    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    print(f"[INFO] Display: {screen_w}x{screen_h}")

    screen = pygame.display.set_mode(
        (screen_w, screen_h),
        pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
    )
    pygame.display.set_caption("BFF Dance")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # Emoji renderer
    emoji_renderer = EmojiRenderer()

    # Detector
    detector = PoseDetector()
    if not detector.initialize():
        print("Erro ao inicializar detector")
        return 1

    # Tentar Kinect primeiro, fallback para Pi Camera
    camera = KinectCapture()
    if camera.initialize():
        print("[INFO] Usando Kinect (640x480)")
        # Ajustar settings para resolução do Kinect
        settings.camera.width = 640
        settings.camera.height = 480
    else:
        print("[INFO] Kinect não encontrado, usando Pi Camera")
        camera = CameraCapture()
        if not camera.initialize():
            print("Erro ao inicializar camera")
            return 1

    # === TELA DE SETUP ===
    player_config = setup_screen(screen, screen_w, screen_h, detector, camera, emoji_renderer)
    if player_config is None:
        camera.release()
        detector.release()
        pygame.quit()
        return 0

    print(f"\nJogadores configurados:")
    for i, p in enumerate(player_config):
        print(f"  {i + 1}: {p['emoji']} {p['emoji_name']}")

    # === JOGO PRINCIPAL ===

    # Avatar renderer
    avatar_renderer = EnhancedAvatarRenderer(screen_w, screen_h, emoji_renderer)
    avatar_renderer.set_scale(settings.camera.width, settings.camera.height)

    # Sistemas
    particles = ParticleSystem()
    collectibles = CollectibleManager(Theme.CUTE)
    easter_eggs = EasterEggDetector()

    # Audio
    audio = AudioManager()
    audio.initialize()

    # Musica - carregar inteira na memoria para evitar falhas
    music_sound = None
    music_file = "/home/admin/projects/bffdance/assets/music/background.mp3"
    if os.path.exists(music_file):
        try:
            music_sound = pygame.mixer.Sound(music_file)
            music_sound.set_volume(0.8)
            music_sound.play(-1)  # Loop infinito
            print(f"[INFO] Musica carregada na memoria: {music_file}")
        except Exception as e:
            print(f"[WARN] Erro musica: {e}")

    # Fontes
    font_large = pygame.font.Font(None, 72)
    font_medium = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 36)

    # Estado
    running = True
    num_players = len(player_config)
    scores = [0] * num_players

    # Tracking por jogador configurado
    cam_w = settings.camera.width
    player_tracking = {}
    for i, cfg in enumerate(player_config):
        if cfg.get('initial_x'):
            player_tracking[i] = cfg['initial_x']
        else:
            # Posicao padrao baseada no lado
            player_tracking[i] = cam_w * 0.7 if cfg['pid'] == 0 else cam_w * 0.3

    tracking_threshold = 400  # Tolerante mas nao demais
    tracking_smoothing = 0.6
    feedback_messages = []
    start_time = time.time()

    # Background
    background = pygame.Surface((screen_w, screen_h))
    draw_gradient_background(background, (40, 20, 60), (20, 40, 80))

    print("\n=== JOGO INICIADO ===")
    print("ESC: Sair")

    try:
        while running:
            dt = clock.get_time() / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            # Capturar
            ret, frame = camera.read()
            if not ret:
                continue

            # Detectar
            raw_poses = detector.detect(frame)

            # Tracking persistente - limitar ao numero de jogadores configurados
            poses = [None] * num_players

            # Encontrar melhor match para cada jogador por proximidade
            used_poses = set()
            for i in range(num_players):
                best_pose = None
                best_dist = tracking_threshold

                for pose in raw_poses:
                    if id(pose) in used_poses:
                        continue
                    center_x = pose.center_x
                    dist = abs(center_x - player_tracking[i])
                    if dist < best_dist:
                        best_dist = dist
                        best_pose = pose

                if best_pose is not None:
                    poses[i] = best_pose
                    used_poses.add(id(best_pose))
                    # Suavizacao do tracking
                    old_x = player_tracking[i]
                    player_tracking[i] = old_x * tracking_smoothing + best_pose.center_x * (1 - tracking_smoothing)

            active_poses = [p for p in poses if p is not None]

            # Coletaveis
            collected = collectibles.update(active_poses)
            for item in collected:
                idx = item.collected_by
                if idx < len(active_poses):
                    collector_pose = active_poses[idx]
                    for pid in range(num_players):
                        if poses[pid] is collector_pose:
                            scores[pid] += item.points
                            ex, ey = avatar_renderer.transform_point(item.x, item.y, mirror=True)
                            particles.emit(ex, ey, count=4, color=player_config[pid]['color'])
                            particles.emit_stars(ex, ey, count=1)
                            feedback_messages.append({
                                'text': f"+{item.points}",
                                'x': ex, 'y': ey,
                                'age': 0,
                                'color': player_config[pid]['color']
                            })
                            audio.play_sound('boing')
                            break

            # Easter eggs (so em modo 2 jogadores)
            if num_players >= 2 and len(active_poses) >= 2:
                egg = easter_eggs.detect(active_poses)
                if egg:
                    bonus_each = egg.bonus_points // num_players
                    for pid in range(num_players):
                        scores[pid] += bonus_each
                    feedback_messages.append({
                        'text': easter_eggs.get_message(egg.type),
                        'x': screen_w // 2, 'y': screen_h // 3,  # Mais acima
                        'age': 0, 'color': (255, 215, 0), 'big': True
                    })

            # Atualizar particulas
            particles.update(dt)

            # === RENDER ===
            screen.blit(background, (0, 0))

            # Piso disco
            elapsed = time.time() - start_time
            draw_disco_floor(screen, elapsed * 2, 100)

            # Particulas
            particles.draw(screen)

            # Avatares
            for pid, pose in enumerate(poses):
                if pose is not None:
                    avatar_renderer.render(
                        screen, pose,
                        player_config[pid]['color'],
                        player_config[pid]['emoji']
                    )

            # Coletaveis
            for c in collectibles.active_collectibles:
                x, y = avatar_renderer.transform_point(c.x, c.y, mirror=True)
                pulse = 1.0 + 0.2 * math.sin(c.age * 4)
                size = int(50 * pulse)

                # Brilho
                glow = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 255, 150, 100), (size, size), size)
                screen.blit(glow, (x - size, y - size))

                # Emoji
                emoji_surf = emoji_renderer.render(c.emoji, size)
                screen.blit(emoji_surf, emoji_surf.get_rect(center=(x, y)))

            # Feedback
            remaining = []
            for msg in feedback_messages:
                msg['age'] += dt
                if msg['age'] < 1.5:
                    remaining.append(msg)
                    alpha = int(255 * (1 - msg['age'] / 1.5))
                    y_off = int(msg['age'] * 60)

                    if msg.get('big'):
                        text = font_large.render(msg['text'], True, msg['color'])
                    else:
                        text = font_medium.render(msg['text'], True, msg['color'])
                    text.set_alpha(alpha)
                    screen.blit(text, text.get_rect(center=(msg['x'], msg['y'] - y_off)))
            feedback_messages[:] = remaining

            # === UI === (so jogadores configurados)
            for pid in range(num_players):
                cfg = player_config[pid]
                # Posicionar: 1 jogador = centro, 2 jogadores = lados
                if num_players == 1:
                    x = screen_w // 2 - 110
                else:
                    x = 30 if pid == 0 else screen_w - 250
                y_base = screen_h - 180

                # Fundo semi-transparente
                ui_bg = pygame.Surface((220, 150), pygame.SRCALPHA)
                pygame.draw.rect(ui_bg, (0, 0, 0, 120), ui_bg.get_rect(), border_radius=10)
                screen.blit(ui_bg, (x - 10, y_base - 10))

                # Emoji + nome
                emoji_small = emoji_renderer.render(cfg['emoji'], 45)
                screen.blit(emoji_small, (x, y_base))

                name_text = font_medium.render(cfg['emoji_name'], True, cfg['color'])
                screen.blit(name_text, (x + 55, y_base + 5))

                # Estrelas
                draw_stars_rating(screen, scores[pid], x, y_base + 55, max_stars=5, size=28)

                # Score
                score_text = font_small.render(f"{scores[pid]} pts", True, (255, 255, 255))
                screen.blit(score_text, (x, y_base + 95))

            # Instrucao
            if len(active_poses) == 0:
                inst = "Entre na frente da camera!" if num_players == 1 else "Entrem na frente da camera!"
            elif num_players == 1:
                inst = "Dance!"
            elif len(active_poses) == 1:
                inst = "Esperando amigo(a)..."
            else:
                inst = "Dancem juntos!"

            inst_text = font_medium.render(inst, True, (255, 255, 255))
            inst_rect = inst_text.get_rect(center=(screen_w // 2, screen_h - 50))
            bg_rect = inst_rect.inflate(30, 15)
            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, (0, 0, 0, 150), bg_surf.get_rect(), border_radius=10)
            screen.blit(bg_surf, bg_rect)
            screen.blit(inst_text, inst_rect)

            # FPS
            fps_text = font_small.render(f"FPS: {clock.get_fps():.0f}", True, (100, 100, 100))
            screen.blit(fps_text, (10, screen_h - 30))

            pygame.display.flip()
            clock.tick(60)

    except KeyboardInterrupt:
        print("\nInterrompido")

    finally:
        if music_sound:
            music_sound.stop()
        camera.release()
        detector.release()
        audio.cleanup()
        pygame.quit()

    print(f"\n=== RESULTADO ===")
    for pid, cfg in enumerate(player_config):
        print(f"{cfg['emoji']} {cfg['emoji_name']}: {scores[pid]} pts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
