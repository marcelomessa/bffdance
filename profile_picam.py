#!/usr/bin/env python3
"""
Profiler para Pi Camera - comparar com Kinect
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')
os.environ['SDL_VIDEODRIVER'] = 'x11'

import pygame
import time
from src.core.pose_detector import PoseDetector, CameraCapture

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
            elapsed = (time.perf_counter() - self.start_time) * 1000
            if self.current not in self.times:
                self.times[self.current] = 0
                self.counts[self.current] = 0
            self.times[self.current] += elapsed
            self.counts[self.current] += 1
        self.current = None
        self.start_time = None
    
    def report(self, title):
        print(f"\n=== {title} ===")
        total = sum(self.times.values())
        for name, total_time in sorted(self.times.items(), key=lambda x: -x[1]):
            count = self.counts[name]
            avg = total_time / count if count > 0 else 0
            pct = (total_time / total * 100) if total > 0 else 0
            print(f"{name:30s}: {avg:6.2f}ms avg ({pct:5.1f}%)")
        frames = self.counts.get('frame_total', 1)
        print(f"{'TOTAL':30s}: {total/frames:6.2f}ms per frame = {1000/(total/frames):.1f} FPS")


def run_test(camera, detector, screen, clock, prof, max_frames=50):
    """Roda teste de profiling"""
    font = pygame.font.Font(None, 48)
    
    frame_count = 0
    while frame_count < max_frames:
        prof.start("frame_total")
        
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
        
        prof.start("camera_read")
        ret, frame = camera.read()
        prof.stop()
        
        if not ret:
            continue
        
        prof.start("pose_detection")
        poses = detector.detect(frame)
        prof.stop()
        
        prof.start("screen_fill")
        screen.fill((30, 30, 50))
        prof.stop()
        
        prof.start("draw_avatars")
        screen_w, screen_h = screen.get_size()
        cam_h, cam_w = frame.shape[:2]
        for pose in poses:
            if len(pose.keypoints) >= 17:
                points = [(int(kp.x * screen_w / cam_w), int(kp.y * screen_h / cam_h)) 
                          for kp in pose.keypoints if kp.confidence > 0.3]
                if len(points) >= 4:
                    pygame.draw.polygon(screen, (255, 100, 150), points[:4], 0)
                for i in range(min(len(points)-1, 10)):
                    pygame.draw.line(screen, (255, 150, 200), points[i], points[i+1], 20)
                for p in points[:12]:
                    pygame.draw.circle(screen, (255, 200, 150), p, 15)
        prof.stop()
        
        prof.start("render_ui")
        text = font.render(f"Frame: {frame_count} | Res: {cam_w}x{cam_h}", True, (255, 255, 255))
        screen.blit(text, (20, 20))
        prof.stop()
        
        prof.start("display_flip")
        pygame.display.flip()
        prof.stop()
        
        prof.stop()  # frame_total
        clock.tick(60)
        frame_count += 1


def main():
    print("=== Profiler Pi Camera ===")
    
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
    
    # Detector
    detector = PoseDetector()
    detector.initialize()
    
    # Teste 1: Pi Camera resolução completa (2304x1296)
    print("\n--- Teste 1: Pi Camera FULL (2304x1296) ---")
    camera_full = CameraCapture()
    camera_full.initialize()
    
    prof1 = Profiler()
    run_test(camera_full, detector, screen, clock, prof1, max_frames=50)
    prof1.report("PI CAMERA FULL (2304x1296)")
    camera_full.release()
    
    # Teste 2: Pi Camera resolução reduzida (640x480)
    print("\n--- Teste 2: Pi Camera 640x480 ---")
    # Modificar settings temporariamente
    from src.config.settings import settings
    old_w, old_h = settings.camera.width, settings.camera.height
    settings.camera.width = 640
    settings.camera.height = 480
    
    camera_low = CameraCapture()
    camera_low.initialize()
    
    prof2 = Profiler()
    run_test(camera_low, detector, screen, clock, prof2, max_frames=50)
    prof2.report("PI CAMERA LOW (640x480)")
    camera_low.release()
    
    # Restaurar settings
    settings.camera.width = old_w
    settings.camera.height = old_h
    
    # Cleanup
    detector.release()
    pygame.quit()
    
    print("\n=== COMPARAÇÃO ===")
    print("Kinect 640x480:    ~57ms camera + ~41ms pose = ~100ms (~10 FPS)")
    print(f"Pi Cam FULL:       ver acima")
    print(f"Pi Cam 640x480:    ver acima")

if __name__ == "__main__":
    main()
