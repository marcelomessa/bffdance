#!/usr/bin/env python3
"""
BFF Dance - Demo completa com coletáveis e easter eggs
"""
import sys
sys.path.insert(0, '/home/admin/projects/bffdance')

import time
from src.core.pose_detector import PoseDetector, CameraCapture
from src.graphics.renderer import Renderer
from src.audio.audio_manager import AudioManager
from src.game.collectibles import CollectibleManager, EasterEggDetector
from src.config.settings import Theme


def main():
    print("=== BFF Dance Demo ===")
    print("Inicializando...")

    # Inicializar componentes
    detector = PoseDetector()
    if not detector.initialize():
        print("Erro ao inicializar detector")
        return 1

    camera = CameraCapture()
    if not camera.initialize():
        print("Erro ao inicializar câmera")
        return 1

    renderer = Renderer()
    if not renderer.initialize():
        print("Erro ao inicializar renderer")
        return 1

    audio = AudioManager()
    audio.initialize()  # Opcional, continua sem som se falhar

    # Sistemas de jogo
    collectibles = CollectibleManager(Theme.MIXED)
    easter_eggs = EasterEggDetector()

    print("\n=== Controles ===")
    print("ESC ou Q: Sair")
    print("Mova as mãos para pegar coletáveis!")
    print("Façam gestos juntos para easter eggs!")
    print("=" * 30)

    running = True
    frame_count = 0
    start_time = time.time()

    # Estado do jogo para demo
    scores = [0, 0]

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

            # Atualizar coletáveis
            collected = collectibles.update(poses)
            for item in collected:
                player = item.collected_by
                scores[player] += item.points
                renderer.show_message(
                    f"+{item.points} {item.emoji}",
                    color=(0, 255, 0),
                    duration=1.0,
                    size=60
                )
                audio.play_sound('boing')

            # Detectar easter eggs
            if len(poses) >= 2:
                egg = easter_eggs.detect(poses)
                if egg:
                    msg = easter_eggs.get_message(egg.type)
                    renderer.show_message(
                        msg,
                        color=(255, 0, 255),
                        duration=2.0,
                        size=80
                    )
                    # Bonus para ambos os jogadores
                    scores[0] += egg.bonus_points // 2
                    scores[1] += egg.bonus_points // 2
                    audio.play_feedback_sound('easter_egg')

            # Montar estado do jogo
            elapsed = time.time() - start_time
            game_state = {
                'players': [
                    {'name': 'Jogador 1', 'score': scores[0]},
                    {'name': 'Jogador 2', 'score': scores[1]},
                ],
                'timer': elapsed,
                'instruction': f'Poses: {len(poses)} | Coletáveis: {len(collectibles.active_collectibles)}',
                'collectibles': [
                    {
                        'x': c.x,
                        'y': c.y,
                        'emoji': c.emoji,
                        'age': c.age
                    }
                    for c in collectibles.active_collectibles
                ]
            }

            # Renderizar
            renderer.render_frame(frame, poses, game_state)

            frame_count += 1

            # Log a cada 5 segundos
            if frame_count % 150 == 0:
                fps = frame_count / (time.time() - start_time)
                print(f"FPS: {fps:.1f} | Poses: {len(poses)} | Scores: {scores}")

    except KeyboardInterrupt:
        print("\nInterrompido")

    finally:
        camera.release()
        detector.release()
        audio.cleanup()
        renderer.cleanup()

    print(f"\nScores finais: Jogador 1: {scores[0]} | Jogador 2: {scores[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
