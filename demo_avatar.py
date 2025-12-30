#!/usr/bin/env python3
"""
BFF Dance - Demo com Avatar (sem vídeo ao vivo)
Renderiza avatares estilizados em vez do feed da câmera
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')

# Forçar driver de vídeo X11 para fullscreen funcionar
os.environ['SDL_VIDEODRIVER'] = 'x11'

import pygame
import time
import math
from src.core.pose_detector import PoseDetector, CameraCapture
from src.graphics.avatar import (
    AvatarRenderer, draw_gradient_background, draw_disco_floor
)
from src.audio.audio_manager import AudioManager
from src.game.collectibles import CollectibleManager, EasterEggDetector
from src.config.settings import settings, Theme


def main():
    print("=== BFF Dance - Avatar Mode ===")
    print("Inicializando...")

    # Inicializar Pygame primeiro
    pygame.init()
    pygame.font.init()

    # Detectar resolução real do display
    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    print(f"[INFO] Display detectado: {screen_w}x{screen_h}")

    # Usar resolução nativa em fullscreen
    screen = pygame.display.set_mode(
        (screen_w, screen_h),
        pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
    )
    print("[INFO] Modo fullscreen")
    pygame.display.set_caption("BFF Dance - Avatar Mode")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # Fontes
    font_large = pygame.font.Font(None, 72)
    font_medium = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 36)

    # Inicializar detector (só precisa da câmera para inferência)
    detector = PoseDetector()
    if not detector.initialize():
        print("Erro ao inicializar detector")
        return 1

    camera = CameraCapture()
    if not camera.initialize():
        print("Erro ao inicializar câmera")
        return 1

    # Avatar renderer - usar tamanho real da tela
    avatar_renderer = AvatarRenderer(screen_w, screen_h)
    avatar_renderer.set_scale(settings.camera.width, settings.camera.height)

    # Audio (opcional)
    audio = AudioManager()
    audio.initialize()

    # Sistemas de jogo
    collectibles = CollectibleManager(Theme.MIXED)
    easter_eggs = EasterEggDetector()

    print("\n=== Modo Avatar ===")
    print("ESC ou Q: Sair")
    print("=" * 30)

    running = True
    frame_count = 0
    start_time = time.time()
    scores = [0, 0]

    # Efeitos visuais de coleta (x, y, idade, cor)
    collect_effects = []

    # Pré-calcular fundo gradiente (otimização)
    background = pygame.Surface((screen_w, screen_h))
    draw_gradient_background(background, (20, 20, 60), (60, 20, 60))

    try:
        while running:
            # Processar eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False

            # Capturar frame (só para inferência, não exibimos)
            ret, frame = camera.read()
            if not ret:
                continue

            # Detectar poses
            poses = detector.detect(frame)

            # Atualizar coletáveis
            collected = collectibles.update(poses)
            for item in collected:
                scores[item.collected_by] += item.points
                audio.play_sound('boing')
                # Adicionar efeito visual na posição do coletável
                ex, ey = avatar_renderer.transform_point(item.x, item.y, mirror=True)
                player_color = (255, 100, 100) if item.collected_by == 0 else (100, 150, 255)
                collect_effects.append([ex, ey, 0.0, player_color, item.points])

            # Detectar easter eggs
            if len(poses) >= 2:
                egg = easter_eggs.detect(poses)
                if egg:
                    scores[0] += egg.bonus_points // 2
                    scores[1] += egg.bonus_points // 2
                    audio.play_feedback_sound('easter_egg')

            # === RENDERIZAÇÃO ===

            # Fundo (blit pré-calculado é rápido)
            screen.blit(background, (0, 0))

            # Piso de discoteca animado
            elapsed = time.time() - start_time
            draw_disco_floor(screen, elapsed * 2, 100)

            # Renderizar avatares
            avatar_renderer.render(screen, poses)

            # Desenhar coletáveis (usar mesma transformação do avatar)
            for c in collectibles.active_collectibles:
                # Usar transform_point do avatar para consistência visual
                x, y = avatar_renderer.transform_point(c.x, c.y, mirror=True)

                # Animação de pulsação
                pulse = 1.0 + 0.15 * math.sin(c.age * 5)
                size = int(50 * pulse)

                # Brilho
                glow_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 255, 100, 80), (size, size), size)
                screen.blit(glow_surf, (x - size, y - size))

                # Emoji/texto do coletável
                emoji_font = pygame.font.Font(None, size)
                emoji_text = emoji_font.render(c.emoji, True, (255, 255, 255))
                emoji_rect = emoji_text.get_rect(center=(x, y))
                screen.blit(emoji_text, emoji_rect)

            # Renderizar efeitos de coleta
            dt = clock.get_time() / 1000.0  # Delta time em segundos
            remaining_effects = []
            for effect in collect_effects:
                ex, ey, age, color, points = effect
                age += dt
                effect[2] = age

                if age < 1.0:  # Efeito dura 1 segundo
                    remaining_effects.append(effect)

                    # Anel expandindo
                    radius = int(50 + age * 150)
                    alpha = int(255 * (1 - age))
                    ring_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(ring_surf, (*color, alpha), (radius, radius), radius, 8)
                    screen.blit(ring_surf, (ex - radius, ey - radius))

                    # Texto de pontos subindo
                    points_y = int(ey - age * 100)
                    points_font = pygame.font.Font(None, 60)
                    points_text = points_font.render(f"+{points}", True, color)
                    points_rect = points_text.get_rect(center=(ex, points_y))
                    screen.blit(points_text, points_rect)

            collect_effects[:] = remaining_effects

            # UI - Scores
            for i, score in enumerate(scores):
                color = (255, 100, 100) if i == 0 else (100, 150, 255)
                x = 30 if i == 0 else screen_w - 200

                # Nome
                name_text = font_medium.render(f"Jogador {i+1}", True, color)
                screen.blit(name_text, (x, 20))

                # Score
                score_text = font_large.render(str(score), True, (255, 255, 255))
                screen.blit(score_text, (x, 60))

            # FPS
            fps = clock.get_fps()
            fps_text = font_small.render(f"FPS: {fps:.0f} | Poses: {len(poses)}", True, (150, 150, 150))
            screen.blit(fps_text, (10, screen_h - 30))

            # Instrução
            instruction = "Dancem juntos!"
            if len(poses) == 0:
                instruction = "Posicionem-se na frente da camera!"
            elif len(poses) == 1:
                instruction = "Esperando segundo jogador..."

            inst_text = font_medium.render(instruction, True, (255, 255, 255))
            inst_rect = inst_text.get_rect(center=(screen_w // 2, screen_h - 60))
            screen.blit(inst_text, inst_rect)

            # Atualizar display
            pygame.display.flip()
            clock.tick(60)  # Limitar a 60 FPS

            frame_count += 1

            # Log a cada 5 segundos
            if frame_count % 300 == 0:
                print(f"FPS: {fps:.1f} | Poses: {len(poses)} | Scores: {scores}")

    except KeyboardInterrupt:
        print("\nInterrompido")

    finally:
        camera.release()
        detector.release()
        audio.cleanup()
        pygame.quit()

    print(f"\nScores finais: Jogador 1: {scores[0]} | Jogador 2: {scores[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
