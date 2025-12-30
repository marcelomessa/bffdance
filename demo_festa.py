#!/usr/bin/env python3
"""
BFF Dance - Demo Festa (versao especial com musica e efeitos)
"""
import sys
import os
sys.path.insert(0, '/home/admin/projects/bffdance')

os.environ['SDL_VIDEODRIVER'] = 'x11'

import pygame
import time
import math
import random
from src.core.pose_detector import PoseDetector, CameraCapture
from src.graphics.avatar import (
    AvatarRenderer, AvatarStyle, draw_gradient_background, draw_disco_floor
)
from src.audio.audio_manager import AudioManager
from src.game.collectibles import CollectibleManager, EasterEggDetector
from src.config.settings import settings, Theme


class ParticleSystem:
    """Sistema de particulas para efeitos visuais"""

    def __init__(self):
        self.particles = []

    def emit(self, x, y, count=10, color=None, speed=100, lifetime=1.0):
        """Emite particulas em uma posicao"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            vel = random.uniform(speed * 0.5, speed)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * vel,
                'vy': math.sin(angle) * vel,
                'life': lifetime,
                'max_life': lifetime,
                'color': color or (255, 255, 100),
                'size': random.randint(4, 12)
            })

    def emit_stars(self, x, y, count=5):
        """Emite estrelas douradas"""
        for _ in range(count):
            angle = random.uniform(-math.pi, 0)  # Para cima
            vel = random.uniform(80, 150)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * vel,
                'vy': math.sin(angle) * vel - 50,
                'life': 1.5,
                'max_life': 1.5,
                'color': (255, 215, 0),  # Dourado
                'size': random.randint(8, 16),
                'star': True
            })

    def emit_confetti(self, screen_w, screen_h, count=30):
        """Emite confete do topo"""
        colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255),
                  (255, 255, 100), (255, 100, 255), (100, 255, 255)]
        for _ in range(count):
            self.particles.append({
                'x': random.randint(0, screen_w),
                'y': -10,
                'vx': random.uniform(-30, 30),
                'vy': random.uniform(100, 200),
                'life': 3.0,
                'max_life': 3.0,
                'color': random.choice(colors),
                'size': random.randint(6, 12),
                'confetti': True
            })

    def update(self, dt):
        """Atualiza particulas"""
        remaining = []
        for p in self.particles:
            p['life'] -= dt
            if p['life'] > 0:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                # Gravidade para confete
                if p.get('confetti'):
                    p['vy'] += 50 * dt
                    p['vx'] += random.uniform(-20, 20) * dt
                remaining.append(p)
        self.particles = remaining

    def draw(self, screen):
        """Desenha particulas"""
        for p in self.particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            color = (*p['color'][:3], alpha)
            size = int(p['size'] * (p['life'] / p['max_life']))

            if p.get('star'):
                # Desenhar estrela
                self._draw_star(screen, int(p['x']), int(p['y']), size, color)
            else:
                # Desenhar circulo
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (size, size), size)
                screen.blit(surf, (int(p['x']) - size, int(p['y']) - size))

    def _draw_star(self, screen, x, y, size, color):
        """Desenha uma estrela"""
        points = []
        for i in range(5):
            # Ponta externa
            angle = math.pi / 2 + i * 2 * math.pi / 5
            points.append((x + size * math.cos(angle), y - size * math.sin(angle)))
            # Ponta interna
            angle += math.pi / 5
            points.append((x + size * 0.4 * math.cos(angle), y - size * 0.4 * math.sin(angle)))

        surf = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        offset_points = [(px - x + size * 1.5, py - y + size * 1.5) for px, py in points]
        if len(offset_points) >= 3:
            pygame.draw.polygon(surf, color, offset_points)
        screen.blit(surf, (x - size * 1.5, y - size * 1.5))


def draw_stars_ui(screen, score, x, y, max_stars=5):
    """Desenha estrelas de pontuacao"""
    # Pontuacao por estrela
    points_per_star = 50
    filled_stars = min(max_stars, score // points_per_star)
    partial = (score % points_per_star) / points_per_star

    star_size = 30
    spacing = 35

    for i in range(max_stars):
        sx = x + i * spacing
        sy = y

        if i < filled_stars:
            # Estrela cheia (dourada)
            color = (255, 215, 0)
            draw_star(screen, sx, sy, star_size, color, filled=True)
        elif i == filled_stars and partial > 0:
            # Estrela parcial
            draw_star(screen, sx, sy, star_size, (100, 100, 100), filled=True)
            # Parte preenchida
            draw_star_partial(screen, sx, sy, star_size, (255, 215, 0), partial)
        else:
            # Estrela vazia
            draw_star(screen, sx, sy, star_size, (100, 100, 100), filled=False)


def draw_star(screen, x, y, size, color, filled=True):
    """Desenha uma estrela"""
    points = []
    for i in range(5):
        angle = -math.pi / 2 + i * 2 * math.pi / 5
        points.append((x + size * math.cos(angle), y + size * math.sin(angle)))
        angle += math.pi / 5
        points.append((x + size * 0.4 * math.cos(angle), y + size * 0.4 * math.sin(angle)))

    if filled:
        pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, (50, 50, 50), points, 2)


def draw_star_partial(screen, x, y, size, color, ratio):
    """Desenha parte de uma estrela (de baixo para cima)"""
    # Simplificado: apenas brilho parcial
    alpha = int(200 * ratio)
    surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    points = []
    for i in range(5):
        angle = -math.pi / 2 + i * 2 * math.pi / 5
        points.append((size + size * math.cos(angle), size + size * math.sin(angle)))
        angle += math.pi / 5
        points.append((size + size * 0.4 * math.cos(angle), size + size * 0.4 * math.sin(angle)))
    pygame.draw.polygon(surf, (*color, alpha), points)
    screen.blit(surf, (x - size, y - size))


def main():
    print("=== BFF Dance - Modo Festa ===")

    # Configuracoes dos jogadores
    player_names = ["Dani", "Amiga"]  # Personalizavel
    player_colors = [(255, 100, 150), (100, 200, 255)]

    # Inicializar Pygame
    pygame.init()
    pygame.font.init()
    pygame.mixer.init()

    # Detectar resolucao
    info = pygame.display.Info()
    screen_w, screen_h = info.current_w, info.current_h
    print(f"[INFO] Display: {screen_w}x{screen_h}")

    # Fullscreen
    screen = pygame.display.set_mode(
        (screen_w, screen_h),
        pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN
    )
    pygame.display.set_caption("BFF Dance - Festa!")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # Fontes
    font_title = pygame.font.Font(None, 96)
    font_large = pygame.font.Font(None, 72)
    font_medium = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 36)

    # Tentar carregar fonte com emoji
    try:
        font_emoji = pygame.font.Font("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 48)
    except:
        font_emoji = font_medium

    # Detector de poses
    detector = PoseDetector()
    if not detector.initialize():
        print("Erro ao inicializar detector")
        return 1

    camera = CameraCapture()
    if not camera.initialize():
        print("Erro ao inicializar camera")
        return 1

    # Avatar
    avatar_renderer = AvatarRenderer(screen_w, screen_h)
    avatar_renderer.set_scale(settings.camera.width, settings.camera.height)

    # Sistemas
    particles = ParticleSystem()
    collectibles = CollectibleManager(Theme.CUTE)  # Tema fofo para criancas
    easter_eggs = EasterEggDetector()

    # Audio
    audio = AudioManager()
    audio.initialize()

    # Tentar carregar musica de fundo
    music_file = "/home/admin/projects/bffdance/assets/music/background.mp3"
    music_playing = False
    if os.path.exists(music_file):
        try:
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(1.0)  # Volume maximo
            pygame.mixer.music.play(-1)  # Loop infinito
            music_playing = True
            print(f"[INFO] Musica carregada: {music_file}")
        except Exception as e:
            print(f"[WARN] Erro ao carregar musica: {e}")
    else:
        print(f"[INFO] Coloque uma musica em: {music_file}")

    # Estado do jogo
    running = True
    frame_count = 0
    start_time = time.time()
    scores = [0, 0]
    collect_effects = []
    last_confetti_time = 0

    # Tracking persistente de jogadores
    # Guarda o centro X de cada jogador para manter identidade
    player_tracking = {0: None, 1: None}  # player_id -> last_center_x
    tracking_threshold = 200  # Distancia maxima para considerar mesmo jogador

    # Pre-calcular fundo
    background = pygame.Surface((screen_w, screen_h))
    draw_gradient_background(background, (40, 20, 60), (20, 40, 80))

    # Mensagens de feedback
    feedback_messages = []

    print("\n=== Modo Festa ===")
    print("ESC ou Q: Sair")
    print("=" * 30)

    try:
        while running:
            dt = clock.get_time() / 1000.0
            current_time = time.time()

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # Confete manual!
                        particles.emit_confetti(screen_w, screen_h, 50)

            # Capturar frame
            ret, frame = camera.read()
            if not ret:
                continue

            # Detectar poses
            raw_poses = detector.detect(frame)

            # Tracking persistente: associar poses aos jogadores conhecidos
            poses = [None, None]  # [jogador0, jogador1]

            for pose in raw_poses:
                center_x = pose.center_x

                # Tentar associar a um jogador existente
                best_player = -1
                best_dist = float('inf')

                for player_id in [0, 1]:
                    if player_tracking[player_id] is not None:
                        dist = abs(center_x - player_tracking[player_id])
                        if dist < tracking_threshold and dist < best_dist:
                            best_dist = dist
                            best_player = player_id

                if best_player >= 0 and poses[best_player] is None:
                    # Associar a jogador existente
                    poses[best_player] = pose
                    player_tracking[best_player] = center_x
                else:
                    # Novo jogador - encontrar slot livre
                    for player_id in [0, 1]:
                        if poses[player_id] is None and player_tracking[player_id] is None:
                            poses[player_id] = pose
                            player_tracking[player_id] = center_x
                            break
                    else:
                        # Ambos ocupados, usar o mais proximo
                        for player_id in [0, 1]:
                            if poses[player_id] is None:
                                poses[player_id] = pose
                                player_tracking[player_id] = center_x
                                break

            # Remover jogadores que sairam (sem pose por muito tempo)
            # Filtrar poses None
            active_poses = [p for p in poses if p is not None]

            # Atualizar coletaveis (usando poses ativas com indices corretos)
            # Criar lista de poses com indice do jogador para pontuacao correta
            collected = collectibles.update(active_poses)
            for item in collected:
                # Encontrar qual jogador (0 ou 1) coletou baseado na pose
                collector_pose_idx = item.collected_by
                if collector_pose_idx < len(active_poses):
                    # Descobrir qual player_id corresponde a essa pose
                    collector_pose = active_poses[collector_pose_idx]
                    for pid in [0, 1]:
                        if poses[pid] is collector_pose:
                            scores[pid] += item.points
                            item.collected_by = pid  # Atualizar para efeitos visuais
                            break
                audio.play_sound('boing')

                # Efeito visual
                ex, ey = avatar_renderer.transform_point(item.x, item.y, mirror=True)
                particles.emit(ex, ey, count=8, color=player_colors[player_id])
                particles.emit_stars(ex, ey, count=2)

                # Feedback
                collect_effects.append([ex, ey, 0.0, player_colors[player_id], item.points])
                feedback_messages.append({
                    'text': f"+{item.points}",
                    'x': ex,
                    'y': ey,
                    'age': 0,
                    'color': player_colors[player_id]
                })

            # Easter eggs
            if len(active_poses) >= 2:
                egg = easter_eggs.detect(active_poses)
                if egg:
                    scores[0] += egg.bonus_points // 2
                    scores[1] += egg.bonus_points // 2
                    audio.play_feedback_sound('easter_egg')
                    # Confete!
                    particles.emit_confetti(screen_w, screen_h, 25)
                    feedback_messages.append({
                        'text': easter_eggs.get_message(egg.type),
                        'x': screen_w // 2,
                        'y': screen_h // 2,
                        'age': 0,
                        'color': (255, 215, 0),
                        'big': True
                    })

            # Confete periodico (menos frequente para CPU)
            if current_time - last_confetti_time > 30:
                particles.emit_confetti(screen_w, screen_h, 15)
                last_confetti_time = current_time

            # Atualizar particulas
            particles.update(dt)

            # === RENDERIZACAO ===

            # Fundo
            screen.blit(background, (0, 0))

            # Piso disco
            elapsed = time.time() - start_time
            draw_disco_floor(screen, elapsed * 2, 100)

            # Particulas (atras dos avatares)
            particles.draw(screen)

            # Avatares (renderizar com cores corretas por jogador)
            for player_id, pose in enumerate(poses):
                if pose is not None:
                    style = AvatarStyle(
                        body_color=player_colors[player_id],
                        head_color=(255, 220, 200),
                        glow_color=player_colors[player_id],
                    )
                    avatar_renderer.render(screen, [pose], styles=[style])

            # Coletaveis
            for c in collectibles.active_collectibles:
                x, y = avatar_renderer.transform_point(c.x, c.y, mirror=True)

                # Pulsacao
                pulse = 1.0 + 0.2 * math.sin(c.age * 4)
                size = int(55 * pulse)

                # Brilho
                glow_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                glow_color = (255, 255, 150, 100)
                pygame.draw.circle(glow_surf, glow_color, (size, size), size)
                screen.blit(glow_surf, (x - size, y - size))

                # Emoji
                emoji_text = font_emoji.render(c.emoji, True, (255, 255, 255))
                emoji_rect = emoji_text.get_rect(center=(x, y))
                screen.blit(emoji_text, emoji_rect)

            # Efeitos de coleta
            remaining_effects = []
            for effect in collect_effects:
                ex, ey, age, color, points = effect
                age += dt
                effect[2] = age

                if age < 1.0:
                    remaining_effects.append(effect)
                    radius = int(50 + age * 150)
                    alpha = int(255 * (1 - age))
                    ring_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(ring_surf, (*color, alpha), (radius, radius), radius, 8)
                    screen.blit(ring_surf, (ex - radius, ey - radius))
            collect_effects[:] = remaining_effects

            # Mensagens de feedback
            remaining_msgs = []
            for msg in feedback_messages:
                msg['age'] += dt
                if msg['age'] < 2.0:
                    remaining_msgs.append(msg)
                    alpha = int(255 * (1 - msg['age'] / 2.0))
                    y_offset = int(msg['age'] * 80)

                    if msg.get('big'):
                        text_surf = font_title.render(msg['text'], True, msg['color'])
                    else:
                        text_surf = font_large.render(msg['text'], True, msg['color'])

                    text_surf.set_alpha(alpha)
                    rect = text_surf.get_rect(center=(msg['x'], msg['y'] - y_offset))
                    screen.blit(text_surf, rect)
            feedback_messages[:] = remaining_msgs

            # === UI ===

            # Painel de jogadores
            for i, (name, score) in enumerate(zip(player_names, scores)):
                color = player_colors[i]

                if i == 0:
                    x = 30
                else:
                    x = screen_w - 220

                # Nome do jogador
                name_text = font_large.render(name, True, color)
                screen.blit(name_text, (x, 20))

                # Estrelas
                draw_stars_ui(screen, score, x, 85, max_stars=5)

                # Score numerico
                score_text = font_medium.render(f"{score} pts", True, (255, 255, 255))
                screen.blit(score_text, (x, 130))

            # Instrucao central
            if len(active_poses) == 0:
                instruction = "Entrem na frente da camera!"
            elif len(active_poses) == 1:
                instruction = "Esperando amiga..."
            else:
                instruction = "Dancem juntas!"

            inst_text = font_medium.render(instruction, True, (255, 255, 255))
            inst_rect = inst_text.get_rect(center=(screen_w // 2, screen_h - 60))

            # Fundo semi-transparente para instrucao
            bg_rect = inst_rect.inflate(40, 20)
            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, (0, 0, 0, 150), bg_surf.get_rect(), border_radius=10)
            screen.blit(bg_surf, bg_rect)
            screen.blit(inst_text, inst_rect)

            # FPS (pequeno)
            fps = clock.get_fps()
            fps_text = font_small.render(f"FPS: {fps:.0f}", True, (100, 100, 100))
            screen.blit(fps_text, (10, screen_h - 30))

            # Atualizar display
            pygame.display.flip()
            clock.tick(60)

            frame_count += 1

            # Log periodico
            if frame_count % 300 == 0:
                print(f"FPS: {fps:.1f} | Poses: {len(poses)} | Scores: {scores}")

    except KeyboardInterrupt:
        print("\nInterrompido")

    finally:
        if music_playing:
            pygame.mixer.music.stop()
        camera.release()
        detector.release()
        audio.cleanup()
        pygame.quit()

    # Resultado final
    print(f"\n{'='*40}")
    print("RESULTADO FINAL")
    print(f"{'='*40}")
    for name, score in zip(player_names, scores):
        stars = min(5, score // 50)
        print(f"{name}: {score} pts {'*' * stars}")
    print(f"{'='*40}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
