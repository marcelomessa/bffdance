"""
BFF Dance - Classe Player
Representa um jogador no jogo
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from ..config.settings import Theme, AgeGroup, get_age_group


class PlayerState(Enum):
    """Estados possíveis do jogador"""
    IDLE = "idle"              # Aguardando
    PERFORMING = "performing"  # Fazendo movimentos (seu turno)
    IMITATING = "imitating"    # Imitando o outro jogador
    READY = "ready"            # Pronto para próxima rodada


@dataclass
class PlayerProfile:
    """Perfil persistente do jogador"""
    id: int = 0
    name: str = "Jogador"
    age: int = 8
    theme: Theme = Theme.MIXED

    @property
    def age_group(self) -> AgeGroup:
        return get_age_group(self.age)


@dataclass
class Player:
    """Jogador ativo no jogo"""
    id: int                           # 0 ou 1 (posição na tela)
    profile: PlayerProfile
    state: PlayerState = PlayerState.IDLE

    # Pontuação da sessão atual
    score: int = 0
    combo: int = 0
    max_combo: int = 0

    # Estatísticas da rodada atual
    round_scores: List[float] = field(default_factory=list)
    easter_eggs_collected: int = 0
    collectibles_grabbed: int = 0

    # Posição na tela (calculada baseado no ID)
    screen_region: tuple = field(default_factory=tuple)  # (x1, y1, x2, y2)

    def add_score(self, points: int, is_perfect: bool = False) -> None:
        """Adiciona pontos ao jogador"""
        if is_perfect:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            # Bonus de combo
            combo_multiplier = 1 + (self.combo * 0.1)  # +10% por combo
            points = int(points * combo_multiplier)
        else:
            self.combo = 0

        self.score += points

    def add_round_score(self, similarity: float) -> int:
        """
        Adiciona score da rodada baseado na similaridade.

        Args:
            similarity: Valor de 0-100 da similaridade

        Returns:
            Pontos ganhos na rodada
        """
        self.round_scores.append(similarity)

        # Calcular pontos
        if similarity >= 90:
            points = 100
            is_perfect = True
        elif similarity >= 70:
            points = 70
            is_perfect = False
        elif similarity >= 50:
            points = 40
            is_perfect = False
        else:
            points = 10
            is_perfect = False

        self.add_score(points, is_perfect)
        return points

    def collect_easter_egg(self, bonus_points: int = 50) -> None:
        """Registra coleta de easter egg"""
        self.easter_eggs_collected += 1
        self.score += bonus_points

    def grab_collectible(self, points: int = 10) -> None:
        """Registra coleta de item"""
        self.collectibles_grabbed += 1
        self.score += points

    def get_average_score(self) -> float:
        """Retorna média dos scores das rodadas"""
        if not self.round_scores:
            return 0.0
        return sum(self.round_scores) / len(self.round_scores)

    def reset_session(self) -> None:
        """Reseta estatísticas para nova sessão"""
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.round_scores = []
        self.easter_eggs_collected = 0
        self.collectibles_grabbed = 0
        self.state = PlayerState.IDLE

    def set_screen_region(self, screen_width: int, screen_height: int) -> None:
        """Define região da tela para este jogador"""
        half_width = screen_width // 2
        if self.id == 0:
            # Jogador 1: lado esquerdo
            self.screen_region = (0, 0, half_width, screen_height)
        else:
            # Jogador 2: lado direito
            self.screen_region = (half_width, 0, screen_width, screen_height)

    def is_in_region(self, x: float, y: float) -> bool:
        """Verifica se coordenada está na região do jogador"""
        if not self.screen_region:
            return False
        x1, y1, x2, y2 = self.screen_region
        return x1 <= x <= x2 and y1 <= y <= y2


def create_default_players() -> tuple:
    """Cria dois jogadores com perfis padrão"""
    player1 = Player(
        id=0,
        profile=PlayerProfile(id=1, name="Jogador 1", age=8, theme=Theme.MIXED)
    )
    player2 = Player(
        id=1,
        profile=PlayerProfile(id=2, name="Jogador 2", age=8, theme=Theme.MIXED)
    )
    return player1, player2
