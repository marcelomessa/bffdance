#!/usr/bin/env python3
"""
BFF Dance - Versão Leve
- Mostra câmera direta (sem avatar desenhado)
- Coletáveis e UI projetados por cima
- Música bufferizada na memória
- Otimizado para baixo consumo de CPU
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')

os.environ['SDL_VIDEODRIVER'] = 'x11'

import pygame
import time
import math
import random
import numpy as np
from src.core.pose_detector import PoseDetector
from src.core.kinect_capture import KinectCapture
from src.config.settings import settings

# Tentar importar cv2 para resize
try:
    import cv2
    HAS_CV2 = True
except:
    HAS_CV2 = False


class SimplifiedGame:
    """Jogo simplificado com câmera direta"""

    def __init__(self):
        self.screen = None
        self.screen_w = 0
        self.screen_h = 0
        self.clock = None
        self.running = False

        # Câmera e detector
        self.camera = None
        self.detector = None

        # Estado do jogo
        self.score = 0
        self.player_name = "Jogador"
        self.player_emoji = "⭐"

        # Coletáveis simples
        self.collectibles = []
        self.last_spawn = 0
        self.spawn_interval = 8.0  # segundos

        # Música
        self.music_sound = None

    def initialize(self):
        """Inicializa o jogo"""
        pygame.init()
        pygame.font.init()

        # Mixer com buffer grande
        pygame.mixer.quit()
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)

        # Display
        info = pygame.display.Info()
        self.screen_w, self.screen_h = info.current_w, info.current_h
        print(f"[INFO] Display: {self.screen_w}x{self.screen_h}")

        self.screen = pygame.display.set_mode(
            (self.screen_w, self.screen_h),
            pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
        )
        pygame.display.set_caption("BFF Dance Leve")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        # Detector de pose
        self.detector = PoseDetector()
        if not self.detector.initialize():
            print("[ERROR] Falha ao inicializar detector")
            return False

        # Kinect
        self.camera = KinectCapture()
        if not self.camera.initialize():
            print("[ERROR] Falha ao inicializar Kinect")
            return False
        print(f"[INFO] Kinect: {self.camera.width}x{self.camera.height}")

        # Carregar música inteira na memória
        music_file = "/home/admin/projects/bffdance/assets/music/background.mp3"
        if os.path.exists(music_file):
            try:
                self.music_sound = pygame.mixer.Sound(music_file)
                self.music_sound.set_volume(0.8)
                print(f"[INFO] Música carregada na memória")
            except Exception as e:
                print(f"[WARN] Erro ao carregar música: {e}")

        # Fontes
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)

        return True

    def spawn_collectible(self):
        """Spawna um coletável nos lados da tela"""
        side = random.choice(['left', 'right'])
        if side == 'left':
            x = random.randint(50, int(self.camera.width * 0.2))
        else:
            x = random.randint(int(self.camera.width * 0.8), self.camera.width - 50)

        y = random.randint(int(self.camera.height * 0.2), int(self.camera.height * 0.7))

        emoji = random.choice(['🌟', '💎', '🎵', '❤️', '🍬'])
        points = random.choice([10, 20, 30])

        self.collectibles.append({
            'x': x, 'y': y,
            'emoji': emoji,
            'points': points,
            'age': 0,
            'lifetime': 10.0
        })

    def check_collection(self, poses):
        """Verifica coleta de itens"""
        GRAB_RADIUS = 50
        WRIST_LEFT = 9
        WRIST_RIGHT = 10

        collected = []

        for pose in poses:
            for wrist_idx in [WRIST_LEFT, WRIST_RIGHT]:
                if wrist_idx < len(pose.keypoints):
                    wrist = pose.keypoints[wrist_idx]
                    if wrist.confidence > 0.3:
                        for c in self.collectibles:
                            dist = math.sqrt((c['x'] - wrist.x)**2 + (c['y'] - wrist.y)**2)
                            if dist < GRAB_RADIUS:
                                collected.append(c)
                                self.score += c['points']

        for c in collected:
            if c in self.collectibles:
                self.collectibles.remove(c)

        return collected

    def run_game(self):
        """Loop principal do jogo"""
        self.running = True
        start_time = time.time()

        # Iniciar música
        if self.music_sound:
            self.music_sound.play(-1)  # Loop infinito

        print("\n=== JOGO INICIADO ===")
        print("ESC: Sair")
        print("Pegue os itens com as mãos!")

        while self.running:
            dt = self.clock.tick(30) / 1000.0
            current_time = time.time()

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Capturar frame
            ret, frame = self.camera.read()
            if not ret:
                continue

            # Detectar poses
            poses = self.detector.detect(frame)

            # Spawnar coletáveis
            if current_time - self.last_spawn > self.spawn_interval:
                if len(self.collectibles) < 3:
                    self.spawn_collectible()
                    self.last_spawn = current_time

            # Atualizar coletáveis (idade)
            remaining = []
            for c in self.collectibles:
                c['age'] += dt
                if c['age'] < c['lifetime']:
                    remaining.append(c)
            self.collectibles = remaining

            # Verificar coletas
            collected = self.check_collection(poses)

            # === RENDERIZAÇÃO ===

            # Converter frame para pygame surface
            # Frame do Kinect é BGR, converter para RGB
            if HAS_CV2:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Redimensionar para tela
                frame_resized = cv2.resize(frame_rgb, (self.screen_w, self.screen_h))
                # Criar surface
                frame_surface = pygame.surfarray.make_surface(frame_resized.swapaxes(0, 1))
            else:
                # Fallback sem cv2 (mais lento)
                frame_rgb = frame[:, :, ::-1]  # BGR to RGB
                frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
                frame_surface = pygame.transform.scale(frame_surface, (self.screen_w, self.screen_h))

            # Espelhar horizontalmente (mais natural)
            frame_surface = pygame.transform.flip(frame_surface, True, False)

            # Desenhar frame
            self.screen.blit(frame_surface, (0, 0))

            # Desenhar coletáveis
            scale_x = self.screen_w / self.camera.width
            scale_y = self.screen_h / self.camera.height

            for c in self.collectibles:
                # Posição na tela (espelhada)
                sx = self.screen_w - int(c['x'] * scale_x)
                sy = int(c['y'] * scale_y)

                # Pulsar
                pulse = 1.0 + 0.2 * math.sin(c['age'] * 4)
                size = int(60 * pulse)

                # Fundo circular
                pygame.draw.circle(self.screen, (255, 255, 255, 180), (sx, sy), size // 2 + 5)
                pygame.draw.circle(self.screen, (255, 200, 0), (sx, sy), size // 2 + 2, 3)

                # Emoji (texto)
                emoji_text = self.font_medium.render(c['emoji'], True, (255, 255, 255))
                emoji_rect = emoji_text.get_rect(center=(sx, sy))
                self.screen.blit(emoji_text, emoji_rect)

            # === UI ===
            # Caixa de score no canto superior
            ui_x, ui_y = 20, 20
            ui_w, ui_h = 200, 80

            ui_bg = pygame.Surface((ui_w, ui_h), pygame.SRCALPHA)
            pygame.draw.rect(ui_bg, (0, 0, 0, 150), ui_bg.get_rect(), border_radius=10)
            self.screen.blit(ui_bg, (ui_x, ui_y))

            # Score
            score_text = self.font_large.render(f"{self.score}", True, (255, 215, 0))
            self.screen.blit(score_text, (ui_x + 20, ui_y + 10))

            pts_text = self.font_small.render("pontos", True, (200, 200, 200))
            self.screen.blit(pts_text, (ui_x + 20, ui_y + 55))

            # FPS no canto
            fps_text = self.font_small.render(f"FPS: {self.clock.get_fps():.0f}", True, (100, 255, 100))
            self.screen.blit(fps_text, (self.screen_w - 120, 20))

            # Instrução na base
            if len(poses) == 0:
                inst = "Entre na frente da câmera!"
            else:
                inst = "Pegue os itens com as mãos!"

            inst_text = self.font_medium.render(inst, True, (255, 255, 255))
            inst_rect = inst_text.get_rect(center=(self.screen_w // 2, self.screen_h - 40))

            bg_rect = inst_rect.inflate(30, 15)
            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, (0, 0, 0, 150), bg_surf.get_rect(), border_radius=10)
            self.screen.blit(bg_surf, bg_rect)
            self.screen.blit(inst_text, inst_rect)

            pygame.display.flip()

        # Parar música
        if self.music_sound:
            self.music_sound.stop()

        print(f"\n=== RESULTADO ===")
        print(f"Pontuação: {self.score}")

    def cleanup(self):
        """Limpa recursos"""
        if self.camera:
            self.camera.release()
        if self.detector:
            self.detector.release()
        pygame.quit()


def main():
    print("=== BFF Dance - Versão Leve ===")
    print("Câmera direta + coletáveis sobrepostos")

    game = SimplifiedGame()

    if not game.initialize():
        print("Falha na inicialização")
        return 1

    try:
        game.run_game()
    except KeyboardInterrupt:
        print("\nInterrompido")
    finally:
        game.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
