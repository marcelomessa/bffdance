"""
BFF Dance - Configurações do Jogo
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum
from pathlib import Path


# Diretórios base
PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
MODELS_DIR = Path("/usr/share/hailo-models")


class Theme(Enum):
    """Temas de coletáveis disponíveis"""
    CUTE = "cute"           # Fofurices: panda, cachorro, capivara, etc
    ADVENTURE = "adventure" # Aventura: astronauta, foguete, carrinho, etc
    MIXED = "mixed"         # Mistureba: todos os itens


class AgeGroup(Enum):
    """Faixas etárias para classificação de conteúdo"""
    KIDS = "kids"           # 4-7 anos
    TWEENS = "tweens"       # 8-12 anos
    TEENS = "teens"         # 13+ anos


@dataclass
class CameraSettings:
    """Configurações da câmera"""
    width: int = 1280
    height: int = 720
    fps: int = 30
    device: int = 0
    # Resolução para inferência (Hailo)
    inference_width: int = 640
    inference_height: int = 640


@dataclass
class HailoSettings:
    """Configurações do Hailo 8"""
    pose_model: str = str(MODELS_DIR / "yolov8s_pose_h8l_pi.hef")
    pose_model_fallback: str = str(MODELS_DIR / "yolov8s_pose_h8.hef")
    confidence_threshold: float = 0.25  # Lowered for better detection
    iou_threshold: float = 0.45


@dataclass
class DisplaySettings:
    """Configurações de exibição"""
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    fps: int = 60
    show_skeleton: bool = True
    show_keypoints: bool = True


@dataclass
class GameplaySettings:
    """Configurações de gameplay"""
    # Detecção de troca de turno
    stillness_threshold: float = 0.02    # Movimento mínimo para considerar "parado"
    stillness_frames: int = 45           # Frames parado = ~1.5s a 30fps

    # Tempo de imitação
    imitation_time_seconds: float = 5.0

    # Pontuação
    perfect_threshold: float = 0.90      # >= 90% = perfeito
    good_threshold: float = 0.70         # >= 70% = bom
    ok_threshold: float = 0.50           # >= 50% = ok

    # Easter eggs
    heart_detection_distance: float = 50.0  # Distância máxima dos pulsos para coração
    collectible_spawn_interval: float = 5.0 # Segundos entre spawn de coletáveis
    collectible_grab_radius: float = 40.0   # Raio para pegar coletável


@dataclass
class AgeContentFilter:
    """
    Filtro de conteúdo por idade.

    NOTA: Todas as funcionalidades estão disponíveis para todas as idades.
    Este filtro apenas restringe conteúdo inapropriado (imagens, músicas, linguagem).
    """
    min_age: int                              # Idade mínima para este nível
    allow_explicit_music: bool = False        # Músicas com letras explícitas
    allow_moderate_language: bool = False     # Linguagem moderada (gírias, etc)
    allow_intense_effects: bool = False       # Efeitos visuais intensos
    content_tags_blocked: List[str] = field(default_factory=list)  # Tags bloqueadas


# Filtros de conteúdo por faixa etária
# Todos têm acesso a TODAS as funcionalidades, apenas conteúdo é filtrado
AGE_CONTENT_FILTERS: Dict[AgeGroup, AgeContentFilter] = {
    AgeGroup.KIDS: AgeContentFilter(
        min_age=4,
        allow_explicit_music=False,
        allow_moderate_language=False,
        allow_intense_effects=False,
        content_tags_blocked=["explicit", "violence", "scary", "adult", "moderate"]
    ),
    AgeGroup.TWEENS: AgeContentFilter(
        min_age=8,
        allow_explicit_music=False,
        allow_moderate_language=True,
        allow_intense_effects=True,
        content_tags_blocked=["explicit", "violence", "adult"]
    ),
    AgeGroup.TEENS: AgeContentFilter(
        min_age=13,
        allow_explicit_music=True,
        allow_moderate_language=True,
        allow_intense_effects=True,
        content_tags_blocked=[]  # Sem restrições
    ),
}


# Mensagens de feedback (mesmas para todas as idades)
FEEDBACK_MESSAGES = {
    "perfect": ["Perfeito!", "Incrível!", "Mandou bem!"],
    "good": ["Muito bom!", "Arrasou!", "Boa!"],
    "ok": ["Bom!", "Legal!", "Valeu!"],
    "miss": ["Quase!", "Tenta de novo!", "Vai que vai!"],
    "easter_egg": ["Easter egg!", "Acharam!", "Surpresa!"],
}


# Sons disponíveis para TODOS (não restritos por idade)
ALL_SOUNDS = ["boing", "risada", "buzina_palhaco", "quack", "mola", "sino", "wow", "airhorn"]

# Surpresas disponíveis para TODOS (não restritas por idade)
ALL_SURPRISES = ["confete", "estrelinhas", "camera_lenta", "filtro_palhaco", "tropeco"]


@dataclass
class AgeContentSettings:
    """Configurações de conteúdo por idade - DEPRECATED, use AgeContentFilter"""
    sounds: List[str] = field(default_factory=list)
    surprises: List[str] = field(default_factory=list)
    messages: Dict[str, str] = field(default_factory=dict)


# Mantido para compatibilidade - será removido
AGE_CONTENT: Dict[AgeGroup, AgeContentSettings] = {
    AgeGroup.KIDS: AgeContentSettings(
        sounds=ALL_SOUNDS,
        surprises=ALL_SURPRISES,
        messages={"perfect": "Perfeito!", "good": "Boa!", "ok": "Legal!", "miss": "Tenta de novo!", "easter_egg": "Uau!"}
    ),
    AgeGroup.TWEENS: AgeContentSettings(
        sounds=ALL_SOUNDS,
        surprises=ALL_SURPRISES,
        messages={"perfect": "Mandou bem!", "good": "Arrasou!", "ok": "Valeu!", "miss": "Quase lá!", "easter_egg": "Massa!"}
    ),
    AgeGroup.TEENS: AgeContentSettings(
        sounds=ALL_SOUNDS,
        surprises=ALL_SURPRISES,
        messages={"perfect": "Perfect!",
            "good": "Nice!",
            "ok": "Ok!",
            "miss": "Opa, foi quase!",
            "easter_egg": "Easter egg!"
        }
    )
}


# Coletáveis por tema
COLLECTIBLES: Dict[Theme, List[Dict]] = {
    Theme.CUTE: [
        {"name": "panda", "emoji": "🐼", "points": 10},
        {"name": "cachorro", "emoji": "🐕", "points": 10},
        {"name": "capivara", "emoji": "🦫", "points": 15},
        {"name": "gatinho", "emoji": "🐱", "points": 10},
        {"name": "coelhinho", "emoji": "🐰", "points": 10},
        {"name": "unicornio", "emoji": "🦄", "points": 20},
    ],
    Theme.ADVENTURE: [
        {"name": "astronauta", "emoji": "👨‍🚀", "points": 15},
        {"name": "foguete", "emoji": "🚀", "points": 20},
        {"name": "carrinho", "emoji": "🏎️", "points": 10},
        {"name": "bola", "emoji": "⚽", "points": 10},
        {"name": "dinossauro", "emoji": "🦖", "points": 15},
        {"name": "robo", "emoji": "🤖", "points": 15},
    ],
    Theme.MIXED: []  # Será preenchido com todos os itens
}

# Preencher tema misto com todos os itens
COLLECTIBLES[Theme.MIXED] = COLLECTIBLES[Theme.CUTE] + COLLECTIBLES[Theme.ADVENTURE]


# Keypoints COCO (YOLOv8 Pose)
KEYPOINT_NAMES = [
    "nose",           # 0
    "left_eye",       # 1
    "right_eye",      # 2
    "left_ear",       # 3
    "right_ear",      # 4
    "left_shoulder",  # 5
    "right_shoulder", # 6
    "left_elbow",     # 7
    "right_elbow",    # 8
    "left_wrist",     # 9
    "right_wrist",    # 10
    "left_hip",       # 11
    "right_hip",      # 12
    "left_knee",      # 13
    "right_knee",     # 14
    "left_ankle",     # 15
    "right_ankle",    # 16
]

# Conexões do esqueleto para desenhar
SKELETON_CONNECTIONS = [
    (0, 1), (0, 2),           # Nariz -> olhos
    (1, 3), (2, 4),           # Olhos -> orelhas
    (5, 6),                    # Ombros
    (5, 7), (7, 9),           # Braço esquerdo
    (6, 8), (8, 10),          # Braço direito
    (5, 11), (6, 12),         # Tronco
    (11, 12),                  # Quadril
    (11, 13), (13, 15),       # Perna esquerda
    (12, 14), (14, 16),       # Perna direita
]

# Cores para os jogadores (RGB)
PLAYER_COLORS = [
    (255, 100, 100),  # Player 1 - Vermelho claro
    (100, 100, 255),  # Player 2 - Azul claro
]


def get_age_group(age: int) -> AgeGroup:
    """Retorna a faixa etária baseada na idade"""
    if age <= 7:
        return AgeGroup.KIDS
    elif age <= 12:
        return AgeGroup.TWEENS
    else:
        return AgeGroup.TEENS


@dataclass
class Settings:
    """Configurações globais do jogo"""
    camera: CameraSettings = field(default_factory=CameraSettings)
    hailo: HailoSettings = field(default_factory=HailoSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
    gameplay: GameplaySettings = field(default_factory=GameplaySettings)


# Instância global de configurações
settings = Settings()
