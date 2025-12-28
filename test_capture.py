#!/usr/bin/env python3
"""
Teste rápido de captura e detecção - salva imagem para verificação
"""
import sys
sys.path.insert(0, '/home/admin/projects/bffdance')

import cv2
import time
from src.core.pose_detector import PoseDetector, CameraCapture, draw_poses

def main():
    print("Inicializando...")

    detector = PoseDetector()
    if not detector.initialize():
        print("Erro ao inicializar detector")
        return 1

    camera = CameraCapture()
    if not camera.initialize():
        print("Erro ao inicializar câmera")
        return 1

    print("Aguardando 2 segundos (posicione-se na frente da câmera)...")
    time.sleep(2)

    # Capturar alguns frames e pegar o melhor
    best_frame = None
    best_poses = []

    for i in range(10):
        ret, frame = camera.read()
        if ret:
            if best_frame is None:
                best_frame = frame  # Guardar pelo menos um frame

            poses = detector.detect(frame)
            if len(poses) > len(best_poses):
                best_poses = poses
                best_frame = frame
            print(f"  Frame {i+1}: {len(poses)} poses detectadas")

    if best_frame is not None:
        # Desenhar poses
        output = draw_poses(best_frame, best_poses)

        # Salvar
        cv2.imwrite("/tmp/bffdance_test.jpg", output)
        cv2.imwrite("/tmp/bffdance_original.jpg", best_frame)

        print(f"\n=== RESULTADO ===")
        print(f"Poses detectadas: {len(best_poses)}")

        for pose in best_poses:
            print(f"\n  Jogador {pose.person_id + 1}:")
            print(f"    Confiança: {pose.confidence:.2%}")
            print(f"    Centro: ({pose.center_x:.0f}, {pose.center_y:.0f})")

            # Mostrar alguns keypoints
            for kp in pose.keypoints[:5]:
                if kp.confidence > 0.3:
                    print(f"    {kp.name}: ({kp.x:.0f}, {kp.y:.0f}) conf={kp.confidence:.2f}")

        print(f"\nImagens salvas:")
        print(f"  /tmp/bffdance_test.jpg (com esqueleto)")
        print(f"  /tmp/bffdance_original.jpg (original)")
    else:
        print("Não foi possível capturar frame")

    camera.release()
    detector.release()
    return 0

if __name__ == "__main__":
    sys.exit(main())
