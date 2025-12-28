"""
BFF Dance - Game Manager
Gerencia estado global do jogo
"""
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Callable

from .player import Player, PlayerState, create_default_players
from ..core.pose_detector import Pose
from ..core.pose_buffer import MultiPlayerPoseBuffer
from ..core.pose_comparator import PoseComparator, ComparisonResult
from ..detection.turn_detector import TurnDetector, TurnEvent, TurnSignal, GestureDetector
from ..config.settings import settings


class GameState(Enum):
    """Estados do jogo"""
    MENU = "menu"                  # Menu principal
    WAITING_PLAYERS = "waiting"    # Aguardando jogadores
    COUNTDOWN = "countdown"        # Contagem regressiva
    PLAYING = "playing"            # Jogando
    ROUND_END = "round_end"        # Fim de rodada (mostrando score)
    GAME_OVER = "game_over"        # Fim de jogo
    PAUSED = "paused"              # Pausado


class GameMode(Enum):
    """Modos de jogo"""
    CHALLENGE = "challenge"        # Modo desafio (faz/imita)
    CHOREOGRAPHY = "choreography"  # Modo coreografia


@dataclass
class RoundResult:
    """Resultado de uma rodada"""
    performer_id: int              # Quem fez a pose
    imitator_id: int               # Quem imitou
    reference_pose: Optional[Pose] # Pose de referência
    imitation_pose: Optional[Pose] # Pose da imitação
    comparison: Optional[ComparisonResult]  # Resultado da comparação
    points_earned: int
    easter_egg_triggered: bool = False


class GameManager:
    """
    Gerenciador principal do jogo.
    Coordena todos os subsistemas.
    """

    def __init__(self):
        # Jogadores
        self.player1, self.player2 = create_default_players()
        self.players = [self.player1, self.player2]

        # Estado
        self.state = GameState.MENU
        self.mode = GameMode.CHALLENGE

        # Subsistemas
        self.pose_buffer = MultiPlayerPoseBuffer(num_players=2)
        self.turn_detector = TurnDetector(self.pose_buffer)
        self.comparator = PoseComparator()

        # Rodada atual
        self.current_round = 0
        self.max_rounds = 10
        self.round_results: List[RoundResult] = []

        # Pose de referência (do performer)
        self.reference_pose: Optional[Pose] = None

        # Callbacks para eventos
        self._on_turn_change: Optional[Callable] = None
        self._on_score: Optional[Callable] = None
        self._on_easter_egg: Optional[Callable] = None

        # Timing
        self.countdown_start: float = 0
        self.countdown_duration: float = 3.0

    def start_game(self, mode: GameMode = GameMode.CHALLENGE) -> None:
        """Inicia um novo jogo"""
        self.mode = mode
        self.current_round = 0
        self.round_results = []
        self.reference_pose = None

        # Reset jogadores
        for player in self.players:
            player.reset_session()
            player.set_screen_region(settings.display.width, settings.display.height)

        # Reset subsistemas
        self.turn_detector.reset(starting_player=0)
        self.pose_buffer.clear_all()

        # Iniciar countdown
        self.state = GameState.COUNTDOWN
        self.countdown_start = time.time()

        # Player 0 começa performando
        self.player1.state = PlayerState.PERFORMING
        self.player2.state = PlayerState.IDLE

    def update(self, poses: List[Pose]) -> Optional[dict]:
        """
        Atualiza estado do jogo com novas poses detectadas.

        Args:
            poses: Lista de poses detectadas no frame

        Returns:
            Dict com eventos ocorridos, ou None
        """
        events = {}

        # Atualizar countdown
        if self.state == GameState.COUNTDOWN:
            elapsed = time.time() - self.countdown_start
            if elapsed >= self.countdown_duration:
                self.state = GameState.PLAYING
                events["game_started"] = True
            else:
                events["countdown"] = int(self.countdown_duration - elapsed) + 1
            return events

        # Não processar se não estiver jogando
        if self.state != GameState.PLAYING:
            return None

        # Verificar se temos jogadores suficientes
        if len(poses) < 2:
            events["warning"] = "Aguardando 2 jogadores"
            # Ainda atualizar buffer com poses disponíveis
            self.pose_buffer.add_all(poses)
            return events

        # Verificar easter eggs colaborativos
        if len(poses) >= 2:
            easter_egg = self._check_easter_eggs(poses[0], poses[1])
            if easter_egg:
                events["easter_egg"] = easter_egg

        # Atualizar detector de turno
        turn_event = self.turn_detector.update(poses)

        if turn_event:
            events["turn_change"] = turn_event
            self._handle_turn_change(turn_event, poses)

        # Atualizar info do turno
        current_player = self.turn_detector.get_current_player()
        events["current_player"] = current_player
        events["turn_time"] = self.turn_detector.get_turn_elapsed_time()
        events["remaining_time"] = self.turn_detector.get_turn_remaining_time()

        return events

    def _handle_turn_change(self, event: TurnEvent, poses: List[Pose]) -> None:
        """Processa mudança de turno"""
        performer_id = event.player_id
        imitator_id = 1 - performer_id

        # Se tínhamos uma pose de referência, comparar com a imitação
        if self.reference_pose is not None:
            # Encontrar pose do imitador
            imitator_pose = None
            for pose in poses:
                if pose.person_id == imitator_id:
                    imitator_pose = pose
                    break

            if imitator_pose:
                # Comparar poses
                comparison = self.comparator.compare(self.reference_pose, imitator_pose)

                # Calcular pontos
                points = self.players[imitator_id].add_round_score(comparison.overall_score)

                # Registrar resultado da rodada
                result = RoundResult(
                    performer_id=1 - imitator_id,  # Quem fez a pose original
                    imitator_id=imitator_id,
                    reference_pose=self.reference_pose,
                    imitation_pose=imitator_pose,
                    comparison=comparison,
                    points_earned=points
                )
                self.round_results.append(result)

                self.current_round += 1

                # Callback de score
                if self._on_score:
                    self._on_score(result)

        # Capturar nova pose de referência
        self.reference_pose = event.captured_pose

        # Atualizar estados dos jogadores
        new_performer = self.turn_detector.get_current_player()
        for player in self.players:
            if player.id == new_performer:
                player.state = PlayerState.PERFORMING
            else:
                player.state = PlayerState.IMITATING

        # Verificar fim de jogo
        if self.current_round >= self.max_rounds:
            self.state = GameState.GAME_OVER

        # Callback de mudança de turno
        if self._on_turn_change:
            self._on_turn_change(event)

    def _check_easter_eggs(self, pose1: Pose, pose2: Pose) -> Optional[str]:
        """Verifica easter eggs colaborativos"""
        # Coração
        if GestureDetector.detect_heart(pose1, pose2):
            for player in self.players:
                player.collect_easter_egg(bonus_points=100)
            if self._on_easter_egg:
                self._on_easter_egg("heart")
            return "heart"

        # High-five
        if GestureDetector.detect_high_five(pose1, pose2):
            for player in self.players:
                player.collect_easter_egg(bonus_points=50)
            if self._on_easter_egg:
                self._on_easter_egg("high_five")
            return "high_five"

        # Pose espelhada
        if GestureDetector.detect_mirror_pose(pose1, pose2):
            for player in self.players:
                player.collect_easter_egg(bonus_points=75)
            if self._on_easter_egg:
                self._on_easter_egg("mirror")
            return "mirror"

        return None

    def get_winner(self) -> Optional[Player]:
        """Retorna o vencedor (ou None se empate)"""
        if self.player1.score > self.player2.score:
            return self.player1
        elif self.player2.score > self.player1.score:
            return self.player2
        return None

    def get_current_performer(self) -> Player:
        """Retorna o jogador que está performando"""
        performer_id = self.turn_detector.get_current_player()
        return self.players[performer_id]

    def get_current_imitator(self) -> Player:
        """Retorna o jogador que está imitando"""
        imitator_id = 1 - self.turn_detector.get_current_player()
        return self.players[imitator_id]

    def pause(self) -> None:
        """Pausa o jogo"""
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED

    def resume(self) -> None:
        """Retoma o jogo"""
        if self.state == GameState.PAUSED:
            self.state = GameState.PLAYING

    def quit_game(self) -> None:
        """Encerra o jogo atual"""
        self.state = GameState.MENU
        self.reference_pose = None

    # Callbacks
    def on_turn_change(self, callback: Callable) -> None:
        """Registra callback para mudança de turno"""
        self._on_turn_change = callback

    def on_score(self, callback: Callable) -> None:
        """Registra callback para quando jogador pontua"""
        self._on_score = callback

    def on_easter_egg(self, callback: Callable) -> None:
        """Registra callback para easter eggs"""
        self._on_easter_egg = callback
