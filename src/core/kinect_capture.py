"""
Kinect v1 capture usando libfreenect
"""
import freenect
import numpy as np
import time


class KinectCapture:
    """Captura de video e profundidade do Kinect v1"""

    def __init__(self):
        self.running = False
        self._initialized = False
        self._last_rgb = None
        self._last_depth = None

    def initialize(self) -> bool:
        """Inicializa o Kinect"""
        try:
            # Testar conexão com uma leitura
            rgb = freenect.sync_get_video()[0]
            if rgb is None:
                print("[WARN] Kinect não retornou video")
                return False

            self._initialized = True
            self.running = True
            print("[INFO] Kinect inicializado: 640x480 RGB + Depth")
            return True
        except Exception as e:
            print(f"[ERROR] Falha ao inicializar Kinect: {e}")
            return False

    def read(self):
        """Lê um frame RGB (junto com depth que é mais rápido)"""
        if not self._initialized:
            return False, None

        try:
            # Ler RGB + Depth juntos é mais rápido que só RGB!
            rgb = freenect.sync_get_video()[0]
            depth = freenect.sync_get_depth()[0]

            if rgb is not None:
                # Converter de RGB para BGR (padrão OpenCV)
                bgr = rgb[:, :, ::-1].copy()
                self._last_rgb = bgr
                self._last_depth = depth
                return True, bgr
            return False, None
        except Exception as e:
            print(f"[ERROR] Kinect read: {e}")
            return False, None

    def read_depth(self):
        """Lê frame de profundidade"""
        if not self._initialized:
            return False, None

        try:
            depth = freenect.sync_get_depth()[0]
            if depth is not None:
                self._last_depth = depth
                return True, depth
            return False, None
        except Exception as e:
            print(f"[ERROR] Kinect depth: {e}")
            return False, None

    def read_both(self):
        """Lê RGB e profundidade"""
        if not self._initialized:
            return False, None, None

        try:
            rgb = freenect.sync_get_video()[0]
            depth = freenect.sync_get_depth()[0]
            if rgb is not None:
                bgr = rgb[:, :, ::-1].copy()
                self._last_rgb = bgr
                self._last_depth = depth
                return True, bgr, depth
            return False, None, None
        except Exception as e:
            print(f"[ERROR] Kinect read_both: {e}")
            return False, None, None

    def get_depth_mask(self, min_dist=500, max_dist=2000):
        """
        Retorna máscara binária de objetos dentro da faixa de distância
        Útil para separar jogadores do fundo

        Args:
            min_dist: Distância mínima em mm (default 0.5m)
            max_dist: Distância máxima em mm (default 2m)

        Returns:
            Máscara binária (255 = dentro da faixa)
        """
        ret, depth = self.read_depth()
        if not ret:
            return None

        mask = np.zeros(depth.shape, dtype=np.uint8)
        mask[(depth >= min_dist) & (depth <= max_dist)] = 255
        return mask

    @property
    def width(self) -> int:
        return 640

    @property
    def height(self) -> int:
        return 480

    def release(self):
        """Libera recursos"""
        self.running = False
        self._initialized = False
        try:
            freenect.sync_stop()
        except:
            pass
        print("[INFO] Kinect liberado")


def test_kinect():
    """Testa captura do Kinect"""
    import cv2

    kinect = KinectCapture()
    if not kinect.initialize():
        print("Falha ao inicializar Kinect")
        return

    print("Pressione 'q' para sair")

    while True:
        ret, rgb, depth = kinect.read_both()
        if ret:
            # Normalizar depth para visualização
            depth_vis = ((depth.astype(float) / 2047) * 255).astype(np.uint8)
            depth_color = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)

            # Mostrar lado a lado
            combined = np.hstack([rgb, depth_color])
            cv2.imshow('Kinect RGB + Depth', combined)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    kinect.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_kinect()
