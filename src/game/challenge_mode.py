"""
BFF Dance - Challenge Mode
Modo principal de jogo: um faz, outro imita
"""
import time
from typing import Optional, Tuple
from dataclasses import dataclass

from .game_manager import GameManager, GameState, GameMode
from .player import PlayerState
from ..core.pose_detector import PoseDetector, CameraCapture, Pose, draw_poses
from ..config.settings import settings, AGE_CONTENT, get_age_group


@dataclass
class ChallengeState:
    """Estado atual do modo desafio"""
    is_running: bool = False
    fps: float = 0.0
    frame_count: int = 0
    last_event: Optional[dict] = None
    last_score_feedback: str = ""
    last_easter_egg: str = ""


class ChallengeMode:
    """
    Modo de jogo Challenge (Desafio).
    Um jogador faz pose, outro imita.
    """

    def __init__(self):
        # Subsistemas
        self.detector = PoseDetector()
        self.camera = CameraCapture()
        self.game = GameManager()

        # Estado
        self.state = ChallengeState()

        # Timing
        self._last_frame_time = 0
        self._fps_update_interval = 0.5
        self._last_fps_update = 0
        self._frame_times = []

        # Feedback
        self._score_feedback_duration = 2.0
        self._score_feedback_time = 0
        self._easter_egg_duration = 3.0
        self._easter_egg_time = 0

        # Callbacks do game manager
        self.game.on_turn_change(self._on_turn_change)
        self.game.on_score(self._on_score)
        self.game.on_easter_egg(self._on_easter_egg)

    def initialize(self) -> bool:
        """Inicializa todos os subsistemas"""
        print("[ChallengeMode] Inicializando...")

        if not self.detector.initialize():
            print("[ERROR] Falha ao inicializar detector")
            return False

        if not self.camera.initialize():
            print("[ERROR] Falha ao inicializar câmera")
            self.detector.release()
            return False

        print("[ChallengeMode] Pronto!")
        return True

    def start(self) -> None:
        """Inicia o modo desafio"""
        self.state.is_running = True
        self.state.frame_count = 0
        self.game.start_game(GameMode.CHALLENGE)
        self._last_frame_time = time.time()

    def stop(self) -> None:
        """Para o modo desafio"""
        self.state.is_running = False
        self.game.quit_game()

    def update(self) -> Tuple[Optional[any], Optional[dict]]:
        """
        Atualiza um frame do jogo.

        Returns:
            (frame_with_overlay, events) ou (None, None) se erro
        """
        if not self.state.is_running:
            return None, None

        # Capturar frame
        ret, frame = self.camera.read()
        if not ret or frame is None:
            return None, None

        # Detectar poses
        poses = self.detector.detect(frame)

        # Atualizar game manager
        events = self.game.update(poses)

        # Atualizar FPS
        self._update_fps()

        # Limpar feedbacks antigos
        self._update_feedbacks()

        # Desenhar overlay
        output_frame = self._draw_overlay(frame, poses, events)

        self.state.frame_count += 1
        self.state.last_event = events

        return output_frame, events

    def _update_fps(self) -> None:
        """Atualiza cálculo de FPS"""
        now = time.time()
        delta = now - self._last_frame_time
        self._last_frame_time = now

        self._frame_times.append(delta)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)

        if now - self._last_fps_update >= self._fps_update_interval:
            if self._frame_times:
                avg_delta = sum(self._frame_times) / len(self._frame_times)
                self.state.fps = 1.0 / avg_delta if avg_delta > 0 else 0
            self._last_fps_update = now

    def _update_feedbacks(self) -> None:
        """Limpa feedbacks expirados"""
        now = time.time()

        if self.state.last_score_feedback and (now - self._score_feedback_time) > self._score_feedback_duration:
            self.state.last_score_feedback = ""

        if self.state.last_easter_egg and (now - self._easter_egg_time) > self._easter_egg_duration:
            self.state.last_easter_egg = ""

    def _draw_overlay(self, frame, poses, events) -> any:
        """Desenha interface do jogo sobre o frame"""
        import cv2

        # Desenhar poses
        output = draw_poses(frame, poses)

        # Info do jogo
        h, w = output.shape[:2]

        # Estado do jogo
        if self.game.state == GameState.COUNTDOWN:
            countdown = events.get("countdown", 0) if events else 0
            self._draw_centered_text(output, str(countdown), (w//2, h//2), scale=4, color=(0, 255, 255))

        elif self.game.state == GameState.PLAYING:
            # Scores
            self._draw_player_info(output, self.game.player1, (10, 30))
            self._draw_player_info(output, self.game.player2, (w - 200, 30))

            # Indicador de quem está jogando
            performer = self.game.get_current_performer()
            indicator_x = 100 if performer.id == 0 else w - 100
            cv2.putText(output, "SUA VEZ!", (indicator_x - 50, h - 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Tempo restante para imitar
            if events and "remaining_time" in events:
                remaining = events["remaining_time"]
                if remaining < settings.gameplay.imitation_time_seconds:
                    color = (0, 255, 0) if remaining > 2 else (0, 165, 255) if remaining > 1 else (0, 0, 255)
                    cv2.putText(output, f"{remaining:.1f}s", (w//2 - 30, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2)

            # Round info
            cv2.putText(output, f"Round {self.game.current_round + 1}/{self.game.max_rounds}",
                       (w//2 - 60, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        elif self.game.state == GameState.GAME_OVER:
            winner = self.game.get_winner()
            if winner:
                text = f"{winner.profile.name} VENCEU!"
            else:
                text = "EMPATE!"
            self._draw_centered_text(output, text, (w//2, h//2), scale=1.5, color=(0, 255, 255))

            # Scores finais
            cv2.putText(output, f"P1: {self.game.player1.score}", (w//2 - 100, h//2 + 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 100), 2)
            cv2.putText(output, f"P2: {self.game.player2.score}", (w//2 + 20, h//2 + 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 255), 2)

        # Feedback de score
        if self.state.last_score_feedback:
            self._draw_centered_text(output, self.state.last_score_feedback,
                                    (w//2, h//2 + 100), scale=1.2, color=(0, 255, 0))

        # Easter egg
        if self.state.last_easter_egg:
            egg_text = {
                "heart": "CORACAO! +100",
                "high_five": "HIGH FIVE! +50",
                "mirror": "ESPELHO! +75"
            }.get(self.state.last_easter_egg, self.state.last_easter_egg)
            self._draw_centered_text(output, egg_text, (w//2, 150), scale=1.5, color=(255, 0, 255))

        # FPS
        cv2.putText(output, f"FPS: {self.state.fps:.1f}", (10, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)

        return output

    def _draw_player_info(self, frame, player, pos) -> None:
        """Desenha info do jogador"""
        import cv2

        x, y = pos
        color = (255, 100, 100) if player.id == 0 else (100, 100, 255)

        cv2.putText(frame, player.profile.name, (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Score: {player.score}", (x, y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        if player.combo > 1:
            cv2.putText(frame, f"Combo: {player.combo}x", (x, y + 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    def _draw_centered_text(self, frame, text, center, scale=1, color=(255, 255, 255)) -> None:
        """Desenha texto centralizado"""
        import cv2

        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = max(1, int(scale * 2))

        (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thickness)
        x = center[0] - text_w // 2
        y = center[1] + text_h // 2

        # Sombra
        cv2.putText(frame, text, (x + 2, y + 2), font, scale, (0, 0, 0), thickness + 1)
        # Texto
        cv2.putText(frame, text, (x, y), font, scale, color, thickness)

    def _on_turn_change(self, event) -> None:
        """Callback de mudança de turno"""
        print(f"[Turn] Player {event.player_id} -> {1 - event.player_id} ({event.signal.value})")

    def _on_score(self, result) -> None:
        """Callback de pontuação"""
        if result.comparison:
            rating = result.comparison.rating
            score = result.comparison.overall_score

            feedback_map = {
                "perfect": "PERFEITO!",
                "good": "MUITO BOM!",
                "ok": "BOM!",
                "miss": "TENTE NOVAMENTE!"
            }
            self.state.last_score_feedback = f"{feedback_map.get(rating, '')} {score:.0f}%"
            self._score_feedback_time = time.time()

            print(f"[Score] P{result.imitator_id + 1}: {score:.1f}% ({rating}) +{result.points_earned}pts")

    def _on_easter_egg(self, egg_type) -> None:
        """Callback de easter egg"""
        self.state.last_easter_egg = egg_type
        self._easter_egg_time = time.time()
        print(f"[Easter Egg] {egg_type}!")

    def release(self) -> None:
        """Libera recursos"""
        self.camera.release()
        self.detector.release()


def run_challenge_mode_test():
    """Testa o modo desafio via terminal (headless)"""
    import time

    print("=" * 50)
    print("BFF Dance - Teste do Modo Desafio")
    print("=" * 50)

    mode = ChallengeMode()

    if not mode.initialize():
        print("[ERRO] Falha na inicialização")
        return 1

    mode.start()
    print("\n[OK] Jogo iniciado!")
    print("Executando por 30 segundos...")
    print("-" * 50)

    start_time = time.time()
    duration = 30

    try:
        while time.time() - start_time < duration:
            frame, events = mode.update()

            if events:
                if "countdown" in events:
                    print(f"  Countdown: {events['countdown']}")
                if "turn_change" in events:
                    print(f"  Turno mudou!")
                if "easter_egg" in events:
                    print(f"  Easter egg: {events['easter_egg']}")

            # Mostrar progresso a cada 5 segundos
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and mode.state.frame_count % 30 == 0:
                print(f"[{elapsed:.0f}s] Frame {mode.state.frame_count} | "
                      f"FPS: {mode.state.fps:.1f} | "
                      f"P1: {mode.game.player1.score} | "
                      f"P2: {mode.game.player2.score}")

    except KeyboardInterrupt:
        print("\n[INFO] Interrompido")
    finally:
        mode.stop()
        mode.release()

    print(f"\n[DONE] Total frames: {mode.state.frame_count}")
    print(f"Scores finais: P1={mode.game.player1.score}, P2={mode.game.player2.score}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run_challenge_mode_test())
