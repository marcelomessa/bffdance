#!/usr/bin/env python3
"""
Teste do renderer Pygame com detecção de poses
"""
import sys
sys.path.insert(0, '/home/admin/projects/bffdance')

import time
from src.core.pose_detector import PoseDetector, CameraCapture
from src.graphics.renderer import Renderer


def main():
    print("Inicializando...")

    # Inicializar detector
    detector = PoseDetector()
    if not detector.initialize():
        print("Erro ao inicializar detector")
        return 1

    # Inicializar câmera
    camera = CameraCapture()
    if not camera.initialize():
        print("Erro ao inicializar câmera")
        return 1

    # Inicializar renderer
    renderer = Renderer()
    if not renderer.initialize():
        print("Erro ao inicializar renderer")
        return 1

    print("Rodando... (ESC ou Q para sair)")

    running = True
    frame_count = 0
    start_time = time.time()

    # Estado de exemplo do jogo
    game_state = {
        'players': [
            {'name': 'Jogador 1', 'score': 0},
            {'name': 'Jogador 2', 'score': 0},
        ],
        'timer': 30.0,
        'current_turn': 0,
        'instruction': 'Faça sua pose!',
    }

    try:
        while running:
            # Processar eventos
            actions = renderer.process_events()
            if 'quit' in actions or 'back' in actions:
                running = False
                continue

            # Capturar frame
            ret, frame = camera.read()
            if not ret:
                continue

            # Detectar poses
            poses = detector.detect(frame)

            # Atualizar estado de exemplo
            elapsed = time.time() - start_time
            game_state['timer'] = max(0, 30 - elapsed)

            # Simular mudança de turno a cada 5 segundos
            game_state['current_turn'] = int(elapsed / 5) % 2

            # Renderizar
            renderer.render_frame(frame, poses, game_state)

            # Contagem de frames
            frame_count += 1

            # Mostrar FPS a cada 60 frames
            if frame_count % 60 == 0:
                fps = frame_count / (time.time() - start_time)
                print(f"FPS: {fps:.1f} | Poses: {len(poses)}")

    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")

    finally:
        # Cleanup
        camera.release()
        detector.release()
        renderer.cleanup()

    total_time = time.time() - start_time
    avg_fps = frame_count / total_time if total_time > 0 else 0
    print(f"\nTotal: {frame_count} frames em {total_time:.1f}s = {avg_fps:.1f} FPS")

    return 0


if __name__ == "__main__":
    sys.exit(main())
