#!/usr/bin/env python3
"""
BFF Dance - Entry Point
Jogo de dança cooperativo para Raspberry Pi 5 com Hailo 8
"""
import sys
import argparse


def run_pose_test():
    """Testa a detecção de poses (modo debug)"""
    import cv2
    from src.core.pose_detector import PoseDetector, CameraCapture, draw_poses

    print("=" * 50)
    print("BFF Dance - Teste de Detecção de Poses")
    print("=" * 50)

    # Inicializar detector
    print("\n[1/2] Inicializando detector Hailo...")
    detector = PoseDetector()
    if not detector.initialize():
        print("[ERRO] Falha ao inicializar detector")
        return 1

    # Inicializar câmera
    print("[2/2] Inicializando câmera...")
    camera = CameraCapture()
    if not camera.initialize():
        print("[ERRO] Falha ao inicializar câmera")
        detector.release()
        return 1

    print("\n[OK] Sistema pronto!")
    print("Pressione 'q' para sair, 's' para salvar screenshot")
    print("-" * 50)

    frame_count = 0
    try:
        while True:
            # Capturar frame
            ret, frame = camera.read()
            if not ret:
                print("[WARN] Falha ao capturar frame")
                continue

            # Detectar poses
            poses = detector.detect(frame)

            # Desenhar poses
            output = draw_poses(frame, poses)

            # Mostrar info
            info_text = f"Poses: {len(poses)} | Frame: {frame_count}"
            cv2.putText(output, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Info de cada jogador
            for i, pose in enumerate(poses):
                y_pos = 60 + i * 25
                player_info = f"P{pose.person_id + 1}: conf={pose.confidence:.2f}"
                cv2.putText(output, player_info, (10, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Exibir
            cv2.imshow("BFF Dance - Pose Test", output)

            # Controles
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f"screenshot_{frame_count}.jpg"
                cv2.imwrite(filename, output)
                print(f"[SAVE] {filename}")

            frame_count += 1

    except KeyboardInterrupt:
        print("\n[INFO] Interrompido pelo usuário")
    finally:
        camera.release()
        detector.release()
        cv2.destroyAllWindows()

    print(f"\n[DONE] Total de frames: {frame_count}")
    return 0


def run_pose_test_headless():
    """Testa detecção de poses sem GUI (para SSH)"""
    import cv2
    import time
    from src.core.pose_detector import PoseDetector, CameraCapture

    print("=" * 50)
    print("BFF Dance - Teste Headless de Detecção de Poses")
    print("=" * 50)

    # Inicializar detector
    print("\n[1/2] Inicializando detector Hailo...")
    detector = PoseDetector()
    if not detector.initialize():
        print("[ERRO] Falha ao inicializar detector")
        return 1

    # Inicializar câmera
    print("[2/2] Inicializando câmera...")
    camera = CameraCapture()
    if not camera.initialize():
        print("[ERRO] Falha ao inicializar câmera")
        detector.release()
        return 1

    print("\n[OK] Sistema pronto!")
    print("Executando por 10 segundos... (Ctrl+C para sair)")
    print("-" * 50)

    frame_count = 0
    start_time = time.time()
    test_duration = 10  # segundos

    try:
        while time.time() - start_time < test_duration:
            # Capturar frame
            ret, frame = camera.read()
            if not ret:
                continue

            # Detectar poses
            poses = detector.detect(frame)

            # Mostrar resultado a cada 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"[{elapsed:.1f}s] Frame {frame_count} | "
                      f"Poses: {len(poses)} | FPS: {fps:.1f}")

                for pose in poses:
                    print(f"  - P{pose.person_id + 1}: "
                          f"center=({pose.center_x:.0f}, {pose.center_y:.0f}) "
                          f"conf={pose.confidence:.2f}")

            frame_count += 1

    except KeyboardInterrupt:
        print("\n[INFO] Interrompido pelo usuário")
    finally:
        camera.release()
        detector.release()

    elapsed = time.time() - start_time
    fps = frame_count / elapsed if elapsed > 0 else 0
    print(f"\n[DONE] {frame_count} frames em {elapsed:.1f}s = {fps:.1f} FPS")
    return 0


def run_game():
    """Executa o jogo principal"""
    print("=" * 50)
    print("BFF Dance - Jogo Principal")
    print("=" * 50)
    print("\n[INFO] Modo jogo ainda não implementado.")
    print("[INFO] Use --test para testar a detecção de poses.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="BFF Dance - Jogo de dança cooperativo"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Executar teste de detecção de poses (com GUI)"
    )
    parser.add_argument(
        "--test-headless",
        action="store_true",
        help="Executar teste de detecção de poses (sem GUI, para SSH)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug com logs extras"
    )

    args = parser.parse_args()

    if args.test:
        return run_pose_test()
    elif args.test_headless:
        return run_pose_test_headless()
    else:
        return run_game()


if __name__ == "__main__":
    sys.exit(main())
