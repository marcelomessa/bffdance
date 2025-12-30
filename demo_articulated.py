#!/usr/bin/env python3
"""
Demo dos avatares articulados com sprites
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')
os.environ['DISPLAY'] = ':0'
os.environ['SDL_VIDEODRIVER'] = 'x11'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from src.core.pose_detector import PoseDetector
from src.core.kinect_capture import KinectCapture
from src.graphics.articulated_avatar import ArticulatedAvatarRenderer

# Personagens disponíveis
CHARACTERS = ['panda', 'monkey', 'penguin', 'rabbit', 'parrot',
              'elephant', 'giraffe', 'hippo', 'pig', 'frog']


def load_background(screen_size):
    """Carrega um background do Kenney"""
    bg_path = "/home/admin/projects/bffdance/assets/backgrounds_kenney/Samples/colored_forest.png"
    try:
        bg = pygame.image.load(bg_path).convert()
        return pygame.transform.scale(bg, screen_size)
    except:
        return None


def main():
    print("=== Demo Avatar Articulado ===")

    pygame.init()
    pygame.font.init()

    # Tela
    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    print(f"Display: {screen_w}x{screen_h}")

    screen = pygame.display.set_mode(
        (screen_w, screen_h),
        pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
    )
    pygame.display.set_caption("BFF Dance - Avatares Articulados")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # Carregar background
    background = load_background((screen_w, screen_h))

    # Detector de pose
    detector = PoseDetector()
    if not detector.initialize():
        print("[ERROR] Falha ao inicializar detector")
        return

    # Kinect
    kinect = KinectCapture()
    if not kinect.initialize():
        print("[ERROR] Falha ao inicializar Kinect")
        detector.release()
        return

    # Renderer articulado
    renderer = ArticulatedAvatarRenderer(screen_w, screen_h)
    renderer.set_scale(kinect.width, kinect.height)

    # Font
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 32)

    # Estado
    player_characters = ['panda', 'monkey']  # Personagens dos jogadores
    char_index = [0, 1]  # Índices nos CHARACTERS

    print("\nControles:")
    print("  1/2: Mudar personagem jogador 1/2")
    print("  ESC: Sair")

    running = True
    frame_count = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_1:
                    # Mudar personagem jogador 1
                    char_index[0] = (char_index[0] + 1) % len(CHARACTERS)
                    player_characters[0] = CHARACTERS[char_index[0]]
                    print(f"Jogador 1: {player_characters[0]}")
                elif event.key == pygame.K_2:
                    # Mudar personagem jogador 2
                    char_index[1] = (char_index[1] + 1) % len(CHARACTERS)
                    player_characters[1] = CHARACTERS[char_index[1]]
                    print(f"Jogador 2: {player_characters[1]}")

        # Capturar frame
        ret, frame = kinect.read()
        if not ret:
            continue

        # Detectar poses
        poses = detector.detect(frame)

        # Desenhar background ou cor sólida
        if background:
            screen.blit(background, (0, 0))
        else:
            # Gradiente manual
            for y in range(screen_h):
                ratio = y / screen_h
                r = int(50 * (1 - ratio) + 30 * ratio)
                g = int(100 * (1 - ratio) + 50 * ratio)
                b = int(150 * (1 - ratio) + 100 * ratio)
                pygame.draw.line(screen, (r, g, b), (0, y), (screen_w, y))

        # Renderizar avatares articulados
        renderer.render(screen, poses, player_characters)

        # UI
        fps = clock.get_fps()
        fps_text = font.render(f"FPS: {fps:.1f}", True, (255, 255, 255))
        screen.blit(fps_text, (20, 20))

        # Info dos personagens
        p1_text = small_font.render(f"P1: {player_characters[0]} (tecla 1)", True, (255, 200, 200))
        p2_text = small_font.render(f"P2: {player_characters[1]} (tecla 2)", True, (200, 200, 255))
        screen.blit(p1_text, (20, 70))
        screen.blit(p2_text, (20, 100))

        poses_text = small_font.render(f"Poses: {len(poses)}", True, (200, 255, 200))
        screen.blit(poses_text, (20, 130))

        pygame.display.flip()
        clock.tick(30)
        frame_count += 1

    # Cleanup
    kinect.release()
    detector.release()
    pygame.quit()
    print("\nDemo finalizado!")


if __name__ == "__main__":
    main()
