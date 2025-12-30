#!/usr/bin/env python3
"""
BFF Dance - Jogo Completo
Modos: Freestyle, Espelho, Desafio
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')
os.environ['DISPLAY'] = ':0'
os.environ['SDL_VIDEODRIVER'] = 'x11'

import pygame
import time
import math
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

from src.core.pose_detector import PoseDetector, CameraCapture
from src.core.kinect_capture import KinectCapture
from src.graphics.avatar import draw_gradient_background, draw_disco_floor
from src.graphics.articulated_avatar import ArticulatedAvatarRenderer
from src.game.collectibles import CollectibleManager, EasterEggDetector
from src.config.settings import settings, Theme


# === ENUMS E CONSTANTES ===

class GameState(Enum):
    MENU = "menu"
    SETUP = "setup"
    PLAYING = "playing"
    PAUSED = "paused"
    RESULTS = "results"


class GameMode(Enum):
    FREESTYLE = "freestyle"
    MIRROR = "mirror"      # Dois dançam juntos, pontos por sincronização
    CHALLENGE = "challenge" # Um faz, outro imita


# Personagens (emoji, nome, sprite_name para articulado)
CHARACTERS = [
    ("🐼", "Panda", "panda"),
    ("🐵", "Macaco", "monkey"),
    ("🐧", "Pinguim", "penguin"),
    ("🐰", "Coelho", "rabbit"),
    ("🦜", "Papagaio", "parrot"),
    ("🐘", "Elefante", "elephant"),
    ("🦒", "Girafa", "giraffe"),
    ("🦛", "Hippo", "hippo"),
    ("🐷", "Porco", "pig"),
    ("🐸", "Sapo", "frog"),
]

PLAYER_COLORS = [
    (255, 100, 150),  # Rosa
    (100, 150, 255),  # Azul
]


# === CLASSES DE SUPORTE ===

@dataclass
class Player:
    id: int
    name: str
    emoji: str
    emoji_name: str
    sprite_name: str
    color: Tuple[int, int, int]
    score: int = 0
    combo: int = 0
    center_x: float = 0
    pose: any = None
    confirmed: bool = False


class SoundManager:
    """Gerencia sons e música"""

    def __init__(self):
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_playing = False
        self.music_sound = None

    def init(self):
        pygame.mixer.quit()
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
        self._load_sounds()

    def _load_sounds(self):
        sfx_path = "/home/admin/projects/bffdance/assets/sfx/Audio"
        jingle_path = "/home/admin/projects/bffdance/assets/music/Hit jingles"

        # Sons de UI
        sound_map = {
            'click': f"{sfx_path}/click1.ogg",
            'select': f"{sfx_path}/switch10.ogg",
            'confirm': f"{sfx_path}/switch33.ogg",
            'back': f"{sfx_path}/switch2.ogg",
        }

        # Jingles para feedback
        if os.path.exists(jingle_path):
            jingle_files = [f for f in os.listdir(jingle_path) if f.endswith('.ogg')]
            for i, jf in enumerate(jingle_files[:5]):
                sound_map[f'jingle_{i}'] = f"{jingle_path}/{jf}"

        for name, path in sound_map.items():
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                    self.sounds[name].set_volume(0.5)
                except:
                    pass

    def play(self, name: str):
        if name in self.sounds:
            self.sounds[name].play()

    def play_jingle(self):
        """Toca um jingle aleatório"""
        jingles = [k for k in self.sounds if k.startswith('jingle_')]
        if jingles:
            self.play(random.choice(jingles))

    def start_music(self, track: str = None):
        if self.music_sound:
            self.music_sound.stop()

        music_files = [
            "/home/admin/projects/bffdance/assets/music/Juhani Junkala [Retro Game Music Pack] Level 1.wav",
            "/home/admin/projects/bffdance/assets/music/Alexander Ehlers - Twists.mp3",
            "/home/admin/projects/bffdance/assets/music/background.mp3",
        ]

        for mf in music_files:
            if os.path.exists(mf):
                try:
                    self.music_sound = pygame.mixer.Sound(mf)
                    self.music_sound.set_volume(0.6)
                    self.music_sound.play(-1)
                    self.music_playing = True
                    print(f"[MUSIC] Playing: {os.path.basename(mf)}")
                    return
                except Exception as e:
                    print(f"[MUSIC] Error: {e}")

    def stop_music(self):
        if self.music_sound:
            self.music_sound.stop()
            self.music_playing = False

    def cleanup(self):
        self.stop_music()


class ParticleSystem:
    """Sistema de partículas"""

    def __init__(self, max_particles=100):
        self.particles = []
        self.max_particles = max_particles

    def emit(self, x, y, count=5, color=(255, 255, 100)):
        if len(self.particles) >= self.max_particles:
            self.particles = self.particles[count:]

        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': 1.0,
                'color': color,
                'size': random.randint(4, 12)
            })

    def emit_burst(self, x, y, color=(255, 215, 0)):
        """Explosão de partículas para eventos especiais"""
        self.emit(x, y, count=15, color=color)

    def update(self, dt):
        remaining = []
        for p in self.particles:
            p['life'] -= dt * 1.5
            if p['life'] > 0:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += 150 * dt  # Gravidade
                remaining.append(p)
        self.particles = remaining

    def draw(self, screen):
        for p in self.particles:
            alpha = max(0, min(255, int(255 * p['life'])))
            size = max(1, int(p['size'] * p['life']))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*p['color'][:3], alpha)
            pygame.draw.circle(surf, color, (size, size), size)
            screen.blit(surf, (int(p['x']) - size, int(p['y']) - size))


class EmojiRenderer:
    """Renderiza emojis com cache"""

    def __init__(self):
        self.font_path = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
        self.fonts = {}
        self.cache = {}
        self._load_fonts()

    def _load_fonts(self):
        for size in [24, 32, 48, 64, 80, 96, 128]:
            try:
                self.fonts[size] = pygame.font.Font(self.font_path, size)
            except:
                self.fonts[size] = pygame.font.Font(None, size)

    def render(self, emoji: str, size: int = 48) -> pygame.Surface:
        cache_key = (emoji, size)
        if cache_key in self.cache:
            return self.cache[cache_key]

        available = sorted(self.fonts.keys())
        best_size = min(available, key=lambda x: abs(x - size))
        font = self.fonts[best_size]

        try:
            surf = font.render(emoji, True, (255, 255, 255))
            if best_size != size:
                scale = size / best_size
                surf = pygame.transform.scale(surf, (int(surf.get_width() * scale), int(surf.get_height() * scale)))
            self.cache[cache_key] = surf
            return surf
        except:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 200, 100), (size // 2, size // 2), size // 2)
            return surf


# === COMPARADOR DE POSES ===

class PoseComparator:
    """Compara similaridade entre poses"""

    @staticmethod
    def compare(pose1, pose2) -> float:
        """Retorna similaridade 0-100%"""
        if pose1 is None or pose2 is None:
            return 0.0
        if len(pose1.keypoints) < 17 or len(pose2.keypoints) < 17:
            return 0.0

        # Pontos importantes para dança
        important_points = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]  # Ombros, cotovelos, pulsos, quadris, joelhos, tornozelos

        total_diff = 0
        count = 0

        # Normalizar pela distância dos ombros
        def get_shoulder_dist(pose):
            if pose.keypoints[5].confidence > 0.3 and pose.keypoints[6].confidence > 0.3:
                dx = pose.keypoints[5].x - pose.keypoints[6].x
                dy = pose.keypoints[5].y - pose.keypoints[6].y
                return math.sqrt(dx*dx + dy*dy)
            return 100

        norm1 = get_shoulder_dist(pose1)
        norm2 = get_shoulder_dist(pose2)

        for idx in important_points:
            kp1 = pose1.keypoints[idx]
            kp2 = pose2.keypoints[idx]

            if kp1.confidence > 0.3 and kp2.confidence > 0.3:
                # Normalizar coordenadas
                x1 = (kp1.x - pose1.center_x) / norm1
                y1 = (kp1.y - pose1.center_y) / norm1
                x2 = (kp2.x - pose2.center_x) / norm2
                y2 = (kp2.y - pose2.center_y) / norm2

                diff = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                total_diff += diff
                count += 1

        if count == 0:
            return 0.0

        avg_diff = total_diff / count
        # Converter diferença em similaridade (0-100%)
        similarity = max(0, 100 - avg_diff * 100)
        return similarity


# === JOGO PRINCIPAL ===

class BFFDanceGame:
    """Classe principal do jogo"""

    def __init__(self):
        self.screen = None
        self.screen_w = 0
        self.screen_h = 0
        self.clock = None

        self.detector = None
        self.camera = None

        self.sound = SoundManager()
        self.emoji_renderer = None
        self.avatar_renderer = None
        self.particles = ParticleSystem()
        self.collectibles = None
        self.easter_eggs = None

        self.state = GameState.MENU
        self.mode = GameMode.FREESTYLE
        self.players: List[Player] = []

        self.fonts = {}
        self.running = True

        # Estado do modo espelho
        self.mirror_score = 0
        self.mirror_streak = 0
        self.last_similarity = 0

        # Estado do modo desafio
        self.challenge_leader = 0
        self.challenge_reference_pose = None
        self.challenge_round = 0
        self.challenge_turn_start = 0

        # Feedback
        self.feedback_messages = []
        self.game_start_time = 0

    def init(self) -> bool:
        """Inicializa o jogo"""
        pygame.init()
        pygame.font.init()

        info = pygame.display.Info()
        self.screen_w, self.screen_h = info.current_w, info.current_h
        print(f"[INIT] Display: {self.screen_w}x{self.screen_h}")

        self.screen = pygame.display.set_mode(
            (self.screen_w, self.screen_h),
            pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
        )
        pygame.display.set_caption("BFF Dance")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        # Sons
        self.sound.init()

        # Fontes
        self.fonts['title'] = pygame.font.Font(None, 100)
        self.fonts['large'] = pygame.font.Font(None, 72)
        self.fonts['medium'] = pygame.font.Font(None, 48)
        self.fonts['small'] = pygame.font.Font(None, 36)

        # Renderizadores
        self.emoji_renderer = EmojiRenderer()
        self.avatar_renderer = ArticulatedAvatarRenderer(self.screen_w, self.screen_h)

        # Detector de poses
        self.detector = PoseDetector()
        if not self.detector.initialize():
            print("[ERROR] Falha ao inicializar detector")
            return False

        # Câmera (Kinect ou Pi Camera)
        self.camera = KinectCapture()
        if self.camera.initialize():
            print("[INIT] Usando Kinect")
            settings.camera.width = 640
            settings.camera.height = 480
        else:
            print("[INIT] Usando Pi Camera")
            self.camera = CameraCapture()
            if not self.camera.initialize():
                print("[ERROR] Falha ao inicializar câmera")
                return False

        self.avatar_renderer.set_scale(settings.camera.width, settings.camera.height)

        # Sistemas de jogo
        self.collectibles = CollectibleManager(Theme.CUTE)
        self.easter_eggs = EasterEggDetector()

        return True

    def run(self):
        """Loop principal"""
        while self.running:
            dt = self.clock.get_time() / 1000.0

            self._handle_events()

            if self.state == GameState.MENU:
                self._update_menu()
                self._render_menu()
            elif self.state == GameState.SETUP:
                self._update_setup()
                self._render_setup()
            elif self.state == GameState.PLAYING:
                self._update_game(dt)
                self._render_game()
            elif self.state == GameState.RESULTS:
                self._update_results()
                self._render_results()

            pygame.display.flip()
            self.clock.tick(30)

        self._cleanup()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.PLAYING:
                        self.state = GameState.RESULTS
                    elif self.state in (GameState.SETUP, GameState.RESULTS):
                        self.state = GameState.MENU
                        self.players = []
                        self.sound.stop_music()
                    else:
                        self.running = False
                # Navegação no menu
                elif self.state == GameState.MENU:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        modes = list(GameMode)
                        idx = modes.index(self.mode)
                        self.mode = modes[(idx - 1) % len(modes)]
                        self.sound.play('click')
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        modes = list(GameMode)
                        idx = modes.index(self.mode)
                        self.mode = modes[(idx + 1) % len(modes)]
                        self.sound.play('click')
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = GameState.SETUP
                        self.sound.play('confirm')
                # Atalhos no setup
                elif self.state == GameState.SETUP:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Confirmar todos os jogadores detectados
                        for p in self.players:
                            p.confirmed = True
                        if self.players:
                            self._start_game()

    def _update_menu(self):
        ret, frame = self.camera.read()
        if ret:
            poses = self.detector.detect(frame)
            # Detectar gestos para selecionar modo
            for pose in poses:
                left_up, right_up = self._get_raised_hands(pose)
                if left_up and right_up:
                    # Duas mãos = iniciar
                    self.state = GameState.SETUP
                    self.sound.play('confirm')

    def _render_menu(self):
        # Background
        draw_gradient_background(self.screen, (30, 20, 50), (50, 30, 70))

        # Título
        title = self.fonts['title'].render("BFF Dance", True, (255, 200, 100))
        self.screen.blit(title, title.get_rect(center=(self.screen_w // 2, 150)))

        # Modos
        modes = [
            (GameMode.FREESTYLE, "Freestyle", "Dance livremente!"),
            (GameMode.MIRROR, "Espelho", "Dancem sincronizados!"),
            (GameMode.CHALLENGE, "Desafio", "Um faz, outro imita!"),
        ]

        y = 350
        for i, (mode, name, desc) in enumerate(modes):
            selected = mode == self.mode
            color = (255, 255, 100) if selected else (200, 200, 200)

            # Box
            box_w, box_h = 400, 100
            box_x = self.screen_w // 2 - box_w // 2
            box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            bg_color = (80, 60, 100, 200) if selected else (40, 30, 60, 150)
            pygame.draw.rect(box_surf, bg_color, box_surf.get_rect(), border_radius=15)
            pygame.draw.rect(box_surf, color, box_surf.get_rect(), 3, border_radius=15)
            self.screen.blit(box_surf, (box_x, y))

            # Texto
            name_text = self.fonts['large'].render(name, True, color)
            self.screen.blit(name_text, name_text.get_rect(center=(self.screen_w // 2, y + 35)))
            desc_text = self.fonts['small'].render(desc, True, (180, 180, 180))
            self.screen.blit(desc_text, desc_text.get_rect(center=(self.screen_w // 2, y + 70)))

            y += 130

        # Instruções
        inst = "Levante as DUAS MÃOS para iniciar"
        inst_text = self.fonts['medium'].render(inst, True, (150, 150, 150))
        self.screen.blit(inst_text, inst_text.get_rect(center=(self.screen_w // 2, self.screen_h - 80)))

        # Setas para mudar modo
        hint = "← → para mudar modo"
        hint_text = self.fonts['small'].render(hint, True, (100, 100, 100))
        self.screen.blit(hint_text, hint_text.get_rect(center=(self.screen_w // 2, self.screen_h - 40)))

    def _update_setup(self):
        """Tela de seleção de personagens"""
        ret, frame = self.camera.read()
        if not ret:
            return

        poses = self.detector.detect(frame)
        current_time = time.time()

        # Tracking de jogadores
        used_poses = set()
        for player in self.players:
            best_pose = None
            best_dist = 300
            for pose in poses:
                if id(pose) in used_poses:
                    continue
                dist = abs(pose.center_x - player.center_x)
                if dist < best_dist:
                    best_dist = dist
                    best_pose = pose
            if best_pose:
                player.pose = best_pose
                player.center_x = best_pose.center_x
                used_poses.add(id(best_pose))
            else:
                player.pose = None

        # Adicionar novos jogadores
        for pose in poses:
            if id(pose) in used_poses:
                continue
            if len(self.players) < 2:
                char_idx = len(self.players)
                emoji, name, sprite = CHARACTERS[char_idx]
                player = Player(
                    id=len(self.players),
                    name=f"Jogador {len(self.players) + 1}",
                    emoji=emoji,
                    emoji_name=name,
                    sprite_name=sprite,
                    color=PLAYER_COLORS[len(self.players)],
                    center_x=pose.center_x,
                    pose=pose
                )
                self.players.append(player)
                used_poses.add(id(pose))
                self.sound.play('select')
                print(f"[SETUP] Jogador {player.id + 1} detectado")

        # Verificar gestos de confirmação
        confirmed_count = sum(1 for p in self.players if p.confirmed)
        for player in self.players:
            if player.pose and not player.confirmed:
                left_up, right_up = self._get_raised_hands(player.pose)
                if left_up and right_up:
                    if not hasattr(player, '_confirm_start'):
                        player._confirm_start = current_time
                    elif current_time - player._confirm_start >= 2.0:
                        player.confirmed = True
                        self.sound.play('confirm')
                        print(f"[SETUP] Jogador {player.id + 1} confirmado!")
                else:
                    player._confirm_start = 0

        # Iniciar jogo
        if confirmed_count >= 1 and len(self.players) >= 1:
            if confirmed_count == len(self.players) or confirmed_count >= 2:
                self._start_game()

    def _render_setup(self):
        draw_gradient_background(self.screen, (30, 30, 70), (70, 30, 70))

        # Renderizar avatares
        for player in self.players:
            if player.pose:
                self.avatar_renderer.render(
                    self.screen, [player.pose], [player.sprite_name]
                )

        # Título
        title = self.fonts['large'].render("Seleção de Personagem", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(self.screen_w // 2, 50)))

        # Painéis dos jogadores
        for i in range(2):
            x = 50 if i == 0 else self.screen_w - 350
            y = 150
            w, h = 300, 300

            # Painel
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (30, 30, 50, 200), panel.get_rect(), border_radius=15)
            color = PLAYER_COLORS[i] if i < len(self.players) else (100, 100, 100)
            pygame.draw.rect(panel, color, panel.get_rect(), 3, border_radius=15)
            self.screen.blit(panel, (x, y))

            if i < len(self.players):
                player = self.players[i]

                # Nome
                name = self.fonts['medium'].render(player.name, True, color)
                self.screen.blit(name, name.get_rect(center=(x + w // 2, y + 40)))

                # Emoji
                emoji_surf = self.emoji_renderer.render(player.emoji, 80)
                self.screen.blit(emoji_surf, emoji_surf.get_rect(center=(x + w // 2, y + 130)))

                # Nome do personagem
                char_name = self.fonts['small'].render(player.emoji_name, True, (200, 200, 200))
                self.screen.blit(char_name, char_name.get_rect(center=(x + w // 2, y + 200)))

                # Status
                if player.confirmed:
                    status = "PRONTO!"
                    status_color = (100, 255, 100)
                elif hasattr(player, '_confirm_start') and player._confirm_start > 0:
                    elapsed = time.time() - player._confirm_start
                    status = f"Segure... {2.0 - elapsed:.1f}s"
                    status_color = (255, 255, 100)
                else:
                    status = "Levante as mãos!"
                    status_color = (255, 200, 100)

                status_text = self.fonts['small'].render(status, True, status_color)
                self.screen.blit(status_text, status_text.get_rect(center=(x + w // 2, y + 260)))
            else:
                waiting = self.fonts['medium'].render("Aguardando...", True, (100, 100, 100))
                self.screen.blit(waiting, waiting.get_rect(center=(x + w // 2, y + h // 2)))

        # Instruções
        inst = self.fonts['small'].render("Mãos acima da cabeça por 2 segundos para confirmar", True, (180, 180, 180))
        self.screen.blit(inst, inst.get_rect(center=(self.screen_w // 2, self.screen_h - 50)))

    def _start_game(self):
        """Inicia o jogo após setup"""
        self.state = GameState.PLAYING
        self.game_start_time = time.time()
        self.sound.start_music()

        # Reset scores
        for player in self.players:
            player.score = 0
            player.combo = 0

        # Reset estados dos modos
        self.mirror_score = 0
        self.mirror_streak = 0
        self.challenge_round = 0
        self.challenge_leader = 0

        print(f"[GAME] Iniciando modo {self.mode.value} com {len(self.players)} jogadores")

    def _update_game(self, dt):
        """Atualiza lógica do jogo"""
        ret, frame = self.camera.read()
        if not ret:
            return

        poses = self.detector.detect(frame)
        current_time = time.time()

        # Tracking de jogadores
        used_poses = set()
        for player in self.players:
            best_pose = None
            best_dist = 400
            for pose in poses:
                if id(pose) in used_poses:
                    continue
                dist = abs(pose.center_x - player.center_x)
                if dist < best_dist:
                    best_dist = dist
                    best_pose = pose
            if best_pose:
                player.pose = best_pose
                player.center_x = 0.7 * player.center_x + 0.3 * best_pose.center_x
                used_poses.add(id(best_pose))
            else:
                player.pose = None

        active_poses = [p.pose for p in self.players if p.pose]

        # Lógica por modo
        if self.mode == GameMode.FREESTYLE:
            self._update_freestyle(dt, active_poses)
        elif self.mode == GameMode.MIRROR:
            self._update_mirror(dt)
        elif self.mode == GameMode.CHALLENGE:
            self._update_challenge(dt)

        # Easter eggs
        if len(active_poses) >= 2:
            egg = self.easter_eggs.detect(active_poses)
            if egg:
                bonus = egg.bonus_points // len(self.players)
                for player in self.players:
                    player.score += bonus
                self._add_feedback(
                    self.easter_eggs.get_message(egg.type),
                    self.screen_w // 2, self.screen_h // 3,
                    (255, 215, 0), big=True
                )
                self.sound.play_jingle()
                self.particles.emit_burst(self.screen_w // 2, self.screen_h // 3)

        # Partículas
        self.particles.update(dt)

        # Feedback messages
        remaining = []
        for msg in self.feedback_messages:
            msg['age'] += dt
            if msg['age'] < 1.5:
                remaining.append(msg)
        self.feedback_messages = remaining

    def _update_freestyle(self, dt, active_poses):
        """Modo freestyle - coletar itens"""
        collected = self.collectibles.update(active_poses)

        for item in collected:
            if item.collected_by < len(self.players):
                player = self.players[item.collected_by]
                player.score += item.points
                player.combo += 1

                x, y = self.avatar_renderer.transform_point(item.x, item.y)
                self.particles.emit(x, y, count=5, color=player.color)
                self._add_feedback(f"+{item.points}", x, y, player.color)
                self.sound.play('select')

    def _update_mirror(self, dt):
        """Modo espelho - pontuar por sincronização"""
        if len(self.players) < 2:
            return

        p1, p2 = self.players[0], self.players[1]
        if p1.pose and p2.pose:
            similarity = PoseComparator.compare(p1.pose, p2.pose)
            self.last_similarity = similarity

            # Pontuação contínua baseada em sincronização
            if similarity > 70:
                points = int((similarity - 70) / 3)
                for player in self.players:
                    player.score += points
                self.mirror_streak += 1

                if self.mirror_streak % 30 == 0:  # A cada ~1 segundo de sincronia
                    self._add_feedback("SYNC!", self.screen_w // 2, 200, (100, 255, 100), big=True)
                    self.sound.play_jingle()
            else:
                self.mirror_streak = 0

    def _update_challenge(self, dt):
        """Modo desafio - um faz, outro imita"""
        if len(self.players) < 2:
            return

        current_time = time.time()
        leader = self.players[self.challenge_leader]
        follower = self.players[1 - self.challenge_leader]

        # Detectar troca de turno (quando líder fica parado)
        if leader.pose:
            # Guardar pose de referência após 2 segundos parado
            if self.challenge_turn_start == 0:
                self.challenge_turn_start = current_time
            elif current_time - self.challenge_turn_start > 2.0:
                if self.challenge_reference_pose is None:
                    self.challenge_reference_pose = leader.pose
                    self._add_feedback("SUA VEZ!", self.screen_w // 2, 200, (255, 255, 100), big=True)

        # Avaliar imitação
        if self.challenge_reference_pose and follower.pose:
            similarity = PoseComparator.compare(self.challenge_reference_pose, follower.pose)

            if similarity > 80:
                points = int(similarity)
                follower.score += points
                self._add_feedback(f"Perfeito! +{points}", self.screen_w // 2, 300, (100, 255, 100))
                self.sound.play_jingle()

                # Trocar turno
                self.challenge_leader = 1 - self.challenge_leader
                self.challenge_reference_pose = None
                self.challenge_turn_start = 0
                self.challenge_round += 1

    def _render_game(self):
        """Renderiza o jogo"""
        # Background
        draw_gradient_background(self.screen, (40, 20, 60), (20, 40, 80))

        # Piso disco
        elapsed = time.time() - self.game_start_time
        draw_disco_floor(self.screen, elapsed * 2, 100)

        # Partículas
        self.particles.draw(self.screen)

        # Avatares
        active_players = [p for p in self.players if p.pose]
        if active_players:
            poses = [p.pose for p in active_players]
            sprites = [p.sprite_name for p in active_players]
            self.avatar_renderer.render(self.screen, poses, sprites)

        # Coletáveis (modo freestyle)
        if self.mode == GameMode.FREESTYLE:
            for c in self.collectibles.active_collectibles:
                x, y = self.avatar_renderer.transform_point(c.x, c.y)
                pulse = 1.0 + 0.2 * math.sin(c.age * 4)
                size = int(50 * pulse)

                glow = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 255, 150, 100), (size, size), size)
                self.screen.blit(glow, (x - size, y - size))

                emoji_surf = self.emoji_renderer.render(c.emoji, size)
                self.screen.blit(emoji_surf, emoji_surf.get_rect(center=(x, y)))

        # UI - Modo específico
        if self.mode == GameMode.MIRROR:
            # Barra de sincronização
            bar_w = 400
            bar_x = self.screen_w // 2 - bar_w // 2
            pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, 20, bar_w, 30), border_radius=15)
            fill_w = int(bar_w * self.last_similarity / 100)
            color = (100, 255, 100) if self.last_similarity > 70 else (255, 200, 100)
            pygame.draw.rect(self.screen, color, (bar_x, 20, fill_w, 30), border_radius=15)

            sync_text = self.fonts['small'].render(f"Sincronia: {self.last_similarity:.0f}%", True, (255, 255, 255))
            self.screen.blit(sync_text, sync_text.get_rect(center=(self.screen_w // 2, 70)))

        elif self.mode == GameMode.CHALLENGE:
            # Indicar quem é o líder
            leader_text = f"Vez de: Jogador {self.challenge_leader + 1}"
            lt = self.fonts['medium'].render(leader_text, True, PLAYER_COLORS[self.challenge_leader])
            self.screen.blit(lt, lt.get_rect(center=(self.screen_w // 2, 50)))

            round_text = self.fonts['small'].render(f"Rodada {self.challenge_round + 1}", True, (200, 200, 200))
            self.screen.blit(round_text, round_text.get_rect(center=(self.screen_w // 2, 90)))

        # UI - Jogadores
        for i, player in enumerate(self.players):
            x = 30 if i == 0 else self.screen_w - 250
            y = self.screen_h - 150

            ui_bg = pygame.Surface((220, 120), pygame.SRCALPHA)
            pygame.draw.rect(ui_bg, (0, 0, 0, 150), ui_bg.get_rect(), border_radius=10)
            self.screen.blit(ui_bg, (x - 10, y - 10))

            # Emoji + nome
            emoji = self.emoji_renderer.render(player.emoji, 40)
            self.screen.blit(emoji, (x, y))
            name = self.fonts['medium'].render(player.emoji_name, True, player.color)
            self.screen.blit(name, (x + 50, y + 5))

            # Score
            score = self.fonts['small'].render(f"{player.score} pts", True, (255, 255, 255))
            self.screen.blit(score, (x, y + 60))

            # Combo (se houver)
            if player.combo > 1:
                combo = self.fonts['small'].render(f"x{player.combo}", True, (255, 200, 100))
                self.screen.blit(combo, (x + 100, y + 60))

        # Feedback messages
        for msg in self.feedback_messages:
            alpha = int(255 * (1 - msg['age'] / 1.5))
            y_off = int(msg['age'] * 50)

            font = self.fonts['large'] if msg.get('big') else self.fonts['medium']
            text = font.render(msg['text'], True, msg['color'])
            text.set_alpha(alpha)
            self.screen.blit(text, text.get_rect(center=(msg['x'], msg['y'] - y_off)))

        # FPS
        fps = self.fonts['small'].render(f"FPS: {self.clock.get_fps():.0f}", True, (80, 80, 80))
        self.screen.blit(fps, (10, self.screen_h - 30))

    def _update_results(self):
        """Tela de resultados"""
        ret, frame = self.camera.read()
        if ret:
            poses = self.detector.detect(frame)
            for pose in poses:
                left_up, right_up = self._get_raised_hands(pose)
                if left_up and right_up:
                    # Reiniciar
                    self.state = GameState.MENU
                    self.players = []
                    self.sound.stop_music()

    def _render_results(self):
        draw_gradient_background(self.screen, (30, 30, 60), (60, 30, 60))

        # Título
        title = self.fonts['title'].render("Resultado", True, (255, 215, 100))
        self.screen.blit(title, title.get_rect(center=(self.screen_w // 2, 100)))

        # Ordenar por score
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)

        y = 250
        for i, player in enumerate(sorted_players):
            # Posição
            pos_text = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            pos = self.emoji_renderer.render(pos_text, 60)
            self.screen.blit(pos, (self.screen_w // 2 - 200, y))

            # Emoji e nome
            emoji = self.emoji_renderer.render(player.emoji, 50)
            self.screen.blit(emoji, (self.screen_w // 2 - 120, y))

            name = self.fonts['large'].render(player.emoji_name, True, player.color)
            self.screen.blit(name, (self.screen_w // 2 - 50, y + 5))

            # Score
            score = self.fonts['large'].render(f"{player.score} pts", True, (255, 255, 255))
            self.screen.blit(score, (self.screen_w // 2 + 150, y + 5))

            y += 100

        # Instrução
        inst = self.fonts['medium'].render("Levante as mãos para voltar ao menu", True, (150, 150, 150))
        self.screen.blit(inst, inst.get_rect(center=(self.screen_w // 2, self.screen_h - 80)))

    def _add_feedback(self, text: str, x: int, y: int, color: Tuple[int, int, int], big: bool = False):
        self.feedback_messages.append({
            'text': text,
            'x': x,
            'y': y,
            'color': color,
            'age': 0,
            'big': big
        })

    def _get_raised_hands(self, pose) -> Tuple[bool, bool]:
        """Retorna (left_raised, right_raised)"""
        if len(pose.keypoints) < 11:
            return False, False

        left_wrist = pose.keypoints[9]
        right_wrist = pose.keypoints[10]
        left_shoulder = pose.keypoints[5]
        right_shoulder = pose.keypoints[6]

        left_up = (left_wrist.confidence > 0.3 and
                   left_shoulder.confidence > 0.3 and
                   left_wrist.y < left_shoulder.y)
        right_up = (right_wrist.confidence > 0.3 and
                    right_shoulder.confidence > 0.3 and
                    right_wrist.y < right_shoulder.y)

        return left_up, right_up

    def _cleanup(self):
        """Limpa recursos"""
        self.sound.cleanup()
        if self.camera:
            self.camera.release()
        if self.detector:
            self.detector.release()
        pygame.quit()

        print("\n=== Resultado Final ===")
        for player in self.players:
            print(f"{player.emoji} {player.emoji_name}: {player.score} pts")


def main():
    print("=" * 50)
    print("BFF Dance")
    print("=" * 50)

    game = BFFDanceGame()
    if game.init():
        game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
