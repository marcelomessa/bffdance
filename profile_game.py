#!/usr/bin/env python3
"""
Profiler para identificar gargalos de CPU no BFF Dance
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')
os.environ['SDL_VIDEODRIVER'] = 'x11'

import pygame
import time
import numpy as np
from src.core.pose_detector import PoseDetector
from src.core.kinect_capture import KinectCapture

class Profiler:
    def __init__(self):
        self.times = {}
        self.counts = {}
        self.start_time = None
        self.current = None
    
    def start(self, name):
        self.current = name
        self.start_time = time.perf_counter()
    
    def stop(self):
        if self.current and self.start_time:
            elapsed = (time.perf_counter() - self.start_time) * 1000  # ms
            if self.current not in self.times:
                self.times[self.current] = 0
                self.counts[self.current] = 0
            self.times[self.current] += elapsed
            self.counts[self.current] += 1
        self.current = None
        self.start_time = None
    
    def report(self):
        print("\n=== PROFILING REPORT ===")
        total = sum(self.times.values())
        for name, total_time in sorted(self.times.items(), key=lambda x: -x[1]):
            count = self.counts[name]
            avg = total_time / count if count > 0 else 0
            pct = (total_time / total * 100) if total > 0 else 0
            print(f"{name:30s}: {avg:6.2f}ms avg ({pct:5.1f}%) - {count} calls")
        print(f"{'TOTAL':30s}: {total/self.counts.get('frame_total', 1):6.2f}ms per frame")


def main():
    print("=== BFF Dance - Profiler ===")
    
    pygame.init()
    pygame.font.init()
    
    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    print(f"Display: {screen_w}x{screen_h}")
    
    screen = pygame.display.set_mode(
        (screen_w, screen_h),
        pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
    )
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    
    # Inicializar
    prof = Profiler()
    
    prof.start("init_detector")
    detector = PoseDetector()
    detector.initialize()
    prof.stop()
    
    prof.start("init_kinect")
    camera = KinectCapture()
    camera.initialize()
    prof.stop()
    
    # Fontes e recursos
    font = pygame.font.Font(None, 48)
    emoji_font = pygame.font.Font("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 64)
    
    print("\nRodando 100 frames para profiling...")
    print("ESC para sair\n")
    
    frame_count = 0
    max_frames = 100
    
    while frame_count < max_frames:
        prof.start("frame_total")
        
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                frame_count = max_frames
                break
        
        # 1. Captura da câmera
        prof.start("camera_read")
        ret, frame = camera.read()
        prof.stop()
        
        if not ret:
            continue
        
        # 2. Detecção de pose (Hailo)
        prof.start("pose_detection")
        poses = detector.detect(frame)
        prof.stop()
        
        # 3. Limpar tela
        prof.start("screen_fill")
        screen.fill((30, 30, 50))
        prof.stop()
        
        # 4. Desenhar avatares (simulando o que o jogo faz)
        prof.start("draw_avatars")
        for pose in poses:
            if len(pose.keypoints) >= 17:
                # Simular desenho de corpo
                points = [(int(kp.x * screen_w / 640), int(kp.y * screen_h / 480)) 
                          for kp in pose.keypoints if kp.confidence > 0.3]
                
                # Torso (polígono)
                if len(points) >= 4:
                    pygame.draw.polygon(screen, (255, 100, 150), points[:4], 0)
                
                # Linhas dos membros
                for i in range(min(len(points)-1, 10)):
                    pygame.draw.line(screen, (255, 150, 200), points[i], points[i+1], 20)
                
                # Círculos nas juntas
                for p in points[:12]:
                    pygame.draw.circle(screen, (255, 200, 150), p, 15)
        prof.stop()
        
        # 5. Renderizar emoji
        prof.start("render_emoji")
        emoji_surf = emoji_font.render("🐼", True, (255, 255, 255))
        screen.blit(emoji_surf, (100, 100))
        prof.stop()
        
        # 6. Renderizar UI
        prof.start("render_ui")
        text = font.render(f"Frame: {frame_count}", True, (255, 255, 255))
        screen.blit(text, (20, 20))
        fps_text = font.render(f"FPS: {clock.get_fps():.1f}", True, (100, 255, 100))
        screen.blit(fps_text, (20, 60))
        prof.stop()
        
        # 7. Flip do display
        prof.start("display_flip")
        pygame.display.flip()
        prof.stop()
        
        prof.stop()  # frame_total
        
        clock.tick(60)
        frame_count += 1
        
        if frame_count % 20 == 0:
            print(f"Frame {frame_count}/{max_frames}...")
    
    # Relatório
    prof.report()
    
    # Cleanup
    camera.release()
    detector.release()
    pygame.quit()
    
    print("\nDone!")

if __name__ == "__main__":
    main()
