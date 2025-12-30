"""
BFF Dance - Avatar Articulado com Sprites
Renderiza avatares usando sprites de partes do corpo que seguem o esqueleto
"""
import pygame
import math
import os
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from ..core.pose_detector import Pose


# Mapeamento de keypoints COCO
KEYPOINT = {
    'nose': 0,
    'left_eye': 1,
    'right_eye': 2,
    'left_ear': 3,
    'right_ear': 4,
    'left_shoulder': 5,
    'right_shoulder': 6,
    'left_elbow': 7,
    'right_elbow': 8,
    'left_wrist': 9,
    'right_wrist': 10,
    'left_hip': 11,
    'right_hip': 12,
    'left_knee': 13,
    'right_knee': 14,
    'left_ankle': 15,
    'right_ankle': 16,
}


@dataclass
class CharacterSprites:
    """Sprites carregados para um personagem"""
    name: str
    head: pygame.Surface
    torso: pygame.Surface
    upper_arm: pygame.Surface
    lower_arm: pygame.Surface
    hand: pygame.Surface
    upper_leg: pygame.Surface
    lower_leg: pygame.Surface
    foot: pygame.Surface
    joint: pygame.Surface


class ArticulatedAvatarRenderer:
    """Renderiza avatares articulados usando sprites"""

    ASSETS_PATH = "/home/admin/projects/bffdance/assets"
    BODY_PARTS_PATH = f"{ASSETS_PATH}/sprites/body_parts"
    HEADS_PATH = f"{ASSETS_PATH}/sprites/PNG/Round"

    # Personagens disponíveis (nome interno -> nome do arquivo de cabeça)
    CHARACTERS = {
        'panda': 'panda',
        'monkey': 'monkey',
        'penguin': 'penguin',
        'rabbit': 'rabbit',
        'parrot': 'parrot',
        'elephant': 'elephant',
        'giraffe': 'giraffe',
        'hippo': 'hippo',
        'pig': 'pig',
        'snake': 'snake',
        'frog': 'frog',  # Usa body parts do frog, mas cabeça alternativa
        'capybara': 'capybara',  # Usa monkey como cabeça alternativa
    }

    def __init__(self, screen_width: int, screen_height: int):
        self.width = screen_width
        self.height = screen_height
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.body_scale = 0.85

        # Cache de sprites por personagem
        self._sprites_cache: Dict[str, CharacterSprites] = {}

        # Escala dos sprites baseada no tamanho da tela
        self.sprite_scale = min(screen_width, screen_height) / 800

    def set_scale(self, source_width: int, source_height: int):
        """Define escala de conversão das coordenadas"""
        self.scale_x = self.width / source_width
        self.scale_y = self.height / source_height

    def transform_point(self, x: float, y: float, mirror: bool = True) -> Tuple[int, int]:
        """Transforma coordenadas do esqueleto para a tela"""
        sx = x * self.scale_x
        sy = y * self.scale_y
        if mirror:
            sx = self.width - sx

        # Aplicar escala ao redor do centro
        center_x = self.width / 2
        center_y = self.height / 2
        sx = center_x + (sx - center_x) * self.body_scale
        sy = center_y + (sy - center_y) * self.body_scale

        return int(sx), int(sy)

    def load_character_sprites(self, char_name: str) -> Optional[CharacterSprites]:
        """Carrega os sprites de um personagem"""
        if char_name in self._sprites_cache:
            return self._sprites_cache[char_name]

        # Determinar qual conjunto de body parts usar
        body_name = char_name if char_name in self.CHARACTERS else 'panda'

        # Para personagens sem body parts específicos, usar alternativo
        body_path = os.path.join(self.BODY_PARTS_PATH, body_name)
        if not os.path.exists(body_path):
            body_path = os.path.join(self.BODY_PARTS_PATH, 'panda')

        try:
            # Carregar partes do corpo
            torso = pygame.image.load(os.path.join(body_path, 'torso.png')).convert_alpha()
            upper_arm = pygame.image.load(os.path.join(body_path, 'upper_arm.png')).convert_alpha()
            lower_arm = pygame.image.load(os.path.join(body_path, 'lower_arm.png')).convert_alpha()
            hand = pygame.image.load(os.path.join(body_path, 'hand.png')).convert_alpha()
            upper_leg = pygame.image.load(os.path.join(body_path, 'upper_leg.png')).convert_alpha()
            lower_leg = pygame.image.load(os.path.join(body_path, 'lower_leg.png')).convert_alpha()
            foot = pygame.image.load(os.path.join(body_path, 'foot.png')).convert_alpha()
            joint = pygame.image.load(os.path.join(body_path, 'joint.png')).convert_alpha()

            # Carregar cabeça (do pack Kenney)
            head_name = self.CHARACTERS.get(char_name, 'panda')
            head_path = os.path.join(self.HEADS_PATH, f'{head_name}.png')

            # Fallback se não existir
            if not os.path.exists(head_path):
                # Tentar alternativas
                alternatives = ['panda', 'monkey', 'rabbit']
                for alt in alternatives:
                    alt_path = os.path.join(self.HEADS_PATH, f'{alt}.png')
                    if os.path.exists(alt_path):
                        head_path = alt_path
                        break

            head = pygame.image.load(head_path).convert_alpha()

            sprites = CharacterSprites(
                name=char_name,
                head=head,
                torso=torso,
                upper_arm=upper_arm,
                lower_arm=lower_arm,
                hand=hand,
                upper_leg=upper_leg,
                lower_leg=lower_leg,
                foot=foot,
                joint=joint
            )

            self._sprites_cache[char_name] = sprites
            return sprites

        except Exception as e:
            print(f"[WARN] Erro ao carregar sprites de {char_name}: {e}")
            return None

    def _scale_sprite(self, sprite: pygame.Surface, scale: float) -> pygame.Surface:
        """Escala um sprite mantendo aspect ratio"""
        w = int(sprite.get_width() * scale)
        h = int(sprite.get_height() * scale)
        return pygame.transform.smoothscale(sprite, (max(1, w), max(1, h)))

    def _rotate_sprite(self, sprite: pygame.Surface, angle: float) -> Tuple[pygame.Surface, Tuple[int, int]]:
        """Rotaciona sprite e retorna offset do centro"""
        rotated = pygame.transform.rotate(sprite, angle)
        # Calcular offset para manter centro
        offset_x = (rotated.get_width() - sprite.get_width()) // 2
        offset_y = (rotated.get_height() - sprite.get_height()) // 2
        return rotated, (offset_x, offset_y)

    def _calculate_angle(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calcula ângulo entre dois pontos em graus"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.degrees(math.atan2(-dy, dx)) - 90

    def _calculate_distance(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calcula distância entre dois pontos"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    def _draw_limb(
        self,
        screen: pygame.Surface,
        sprite: pygame.Surface,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        base_scale: float
    ):
        """Desenha um membro entre dois pontos"""
        # Calcular ângulo e distância
        angle = self._calculate_angle(start_pos, end_pos)
        distance = self._calculate_distance(start_pos, end_pos)

        # Escalar sprite baseado na distância (mantendo proporções razoáveis)
        original_height = sprite.get_height()
        scale = (distance / original_height) * base_scale if original_height > 0 else base_scale

        # Limitar escala
        scale = max(0.3, min(scale, 2.0))

        # Escalar e rotacionar
        scaled = self._scale_sprite(sprite, scale)
        rotated, offset = self._rotate_sprite(scaled, angle)

        # Posicionar no ponto médio
        mid_x = (start_pos[0] + end_pos[0]) // 2
        mid_y = (start_pos[1] + end_pos[1]) // 2

        pos = (
            mid_x - rotated.get_width() // 2,
            mid_y - rotated.get_height() // 2
        )

        screen.blit(rotated, pos)

    def _draw_joint(
        self,
        screen: pygame.Surface,
        sprite: pygame.Surface,
        pos: Tuple[int, int],
        scale: float
    ):
        """Desenha uma articulação em uma posição"""
        scaled = self._scale_sprite(sprite, scale)
        draw_pos = (
            pos[0] - scaled.get_width() // 2,
            pos[1] - scaled.get_height() // 2
        )
        screen.blit(scaled, draw_pos)

    def render(
        self,
        screen: pygame.Surface,
        poses: List[Pose],
        character_names: Optional[List[str]] = None
    ):
        """
        Renderiza avatares articulados para todas as poses.

        Args:
            screen: Superfície Pygame
            poses: Lista de poses detectadas
            character_names: Lista de nomes de personagens (opcional)
        """
        if character_names is None:
            character_names = ['panda', 'monkey']

        for i, pose in enumerate(poses):
            char_name = character_names[i % len(character_names)]
            self._render_character(screen, pose, char_name)

    def _render_character(
        self,
        screen: pygame.Surface,
        pose: Pose,
        char_name: str
    ):
        """Renderiza um personagem articulado"""
        sprites = self.load_character_sprites(char_name)
        if sprites is None:
            return

        keypoints = pose.keypoints
        if len(keypoints) < 17:
            return

        # Extrair pontos com confiança suficiente
        points = {}
        for name, idx in KEYPOINT.items():
            if idx < len(keypoints) and keypoints[idx].confidence > 0.3:
                points[name] = self.transform_point(keypoints[idx].x, keypoints[idx].y)

        # Calcular escala baseada na distância dos ombros
        base_scale = self.sprite_scale
        if 'left_shoulder' in points and 'right_shoulder' in points:
            shoulder_dist = self._calculate_distance(points['left_shoulder'], points['right_shoulder'])
            base_scale = shoulder_dist / 150  # Ajustar para tamanho desejado
            base_scale = max(0.5, min(base_scale, 2.5))

        # Desenhar de trás para frente (ordem de renderização)

        # 1. Pernas (atrás)
        self._draw_legs(screen, sprites, points, base_scale)

        # 2. Tronco
        self._draw_torso(screen, sprites, points, base_scale)

        # 3. Braços
        self._draw_arms(screen, sprites, points, base_scale)

        # 4. Cabeça (frente)
        self._draw_head(screen, sprites, points, base_scale)

    def _draw_torso(
        self,
        screen: pygame.Surface,
        sprites: CharacterSprites,
        points: Dict[str, Tuple[int, int]],
        scale: float
    ):
        """Desenha o tronco"""
        # Calcular centro do tronco
        torso_points = ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']
        valid_points = [points[p] for p in torso_points if p in points]

        if len(valid_points) < 2:
            return

        center_x = sum(p[0] for p in valid_points) // len(valid_points)
        center_y = sum(p[1] for p in valid_points) // len(valid_points)

        # Calcular ângulo do tronco
        angle = 0
        if 'left_shoulder' in points and 'right_shoulder' in points:
            angle = self._calculate_angle(points['left_shoulder'], points['right_shoulder']) + 90

        # Escalar e rotacionar
        scaled = self._scale_sprite(sprites.torso, scale * 1.2)
        rotated, _ = self._rotate_sprite(scaled, angle)

        pos = (
            center_x - rotated.get_width() // 2,
            center_y - rotated.get_height() // 2
        )
        screen.blit(rotated, pos)

    def _draw_arms(
        self,
        screen: pygame.Surface,
        sprites: CharacterSprites,
        points: Dict[str, Tuple[int, int]],
        scale: float
    ):
        """Desenha os braços"""
        # Braço esquerdo
        if 'left_shoulder' in points and 'left_elbow' in points:
            self._draw_limb(screen, sprites.upper_arm,
                           points['left_shoulder'], points['left_elbow'], scale)
            self._draw_joint(screen, sprites.joint, points['left_elbow'], scale * 0.8)

        if 'left_elbow' in points and 'left_wrist' in points:
            self._draw_limb(screen, sprites.lower_arm,
                           points['left_elbow'], points['left_wrist'], scale)

        if 'left_wrist' in points:
            self._draw_joint(screen, sprites.hand, points['left_wrist'], scale * 1.0)

        # Braço direito
        if 'right_shoulder' in points and 'right_elbow' in points:
            self._draw_limb(screen, sprites.upper_arm,
                           points['right_shoulder'], points['right_elbow'], scale)
            self._draw_joint(screen, sprites.joint, points['right_elbow'], scale * 0.8)

        if 'right_elbow' in points and 'right_wrist' in points:
            self._draw_limb(screen, sprites.lower_arm,
                           points['right_elbow'], points['right_wrist'], scale)

        if 'right_wrist' in points:
            self._draw_joint(screen, sprites.hand, points['right_wrist'], scale * 1.0)

    def _draw_legs(
        self,
        screen: pygame.Surface,
        sprites: CharacterSprites,
        points: Dict[str, Tuple[int, int]],
        scale: float
    ):
        """Desenha as pernas"""
        # Perna esquerda
        if 'left_hip' in points and 'left_knee' in points:
            self._draw_limb(screen, sprites.upper_leg,
                           points['left_hip'], points['left_knee'], scale)
            self._draw_joint(screen, sprites.joint, points['left_knee'], scale * 0.8)

        if 'left_knee' in points and 'left_ankle' in points:
            self._draw_limb(screen, sprites.lower_leg,
                           points['left_knee'], points['left_ankle'], scale)

        if 'left_ankle' in points:
            self._draw_joint(screen, sprites.foot, points['left_ankle'], scale * 1.0)

        # Perna direita
        if 'right_hip' in points and 'right_knee' in points:
            self._draw_limb(screen, sprites.upper_leg,
                           points['right_hip'], points['right_knee'], scale)
            self._draw_joint(screen, sprites.joint, points['right_knee'], scale * 0.8)

        if 'right_knee' in points and 'right_ankle' in points:
            self._draw_limb(screen, sprites.lower_leg,
                           points['right_knee'], points['right_ankle'], scale)

        if 'right_ankle' in points:
            self._draw_joint(screen, sprites.foot, points['right_ankle'], scale * 1.0)

    def _draw_head(
        self,
        screen: pygame.Surface,
        sprites: CharacterSprites,
        points: Dict[str, Tuple[int, int]],
        scale: float
    ):
        """Desenha a cabeça"""
        # Posição da cabeça
        head_pos = None

        if 'nose' in points:
            head_pos = points['nose']
        elif 'left_eye' in points and 'right_eye' in points:
            head_pos = (
                (points['left_eye'][0] + points['right_eye'][0]) // 2,
                (points['left_eye'][1] + points['right_eye'][1]) // 2
            )

        if head_pos is None:
            return

        # Calcular tamanho da cabeça baseado nos ombros
        head_scale = scale * 0.6
        if 'left_shoulder' in points and 'right_shoulder' in points:
            shoulder_dist = self._calculate_distance(points['left_shoulder'], points['right_shoulder'])
            head_scale = shoulder_dist / 250

        head_scale = max(0.3, min(head_scale, 1.5))

        # Escalar cabeça
        scaled_head = self._scale_sprite(sprites.head, head_scale)

        # Pequena inclinação baseada nos olhos/orelhas
        angle = 0
        if 'left_ear' in points and 'right_ear' in points:
            angle = self._calculate_angle(points['left_ear'], points['right_ear']) + 90
            angle = max(-30, min(angle, 30))  # Limitar inclinação

        if angle != 0:
            scaled_head, _ = self._rotate_sprite(scaled_head, angle)

        # Posicionar cabeça (um pouco acima do nariz)
        pos = (
            head_pos[0] - scaled_head.get_width() // 2,
            head_pos[1] - int(scaled_head.get_height() * 0.6)
        )

        screen.blit(scaled_head, pos)


# Função de conveniência para criar o renderer
def create_articulated_renderer(screen_width: int, screen_height: int) -> ArticulatedAvatarRenderer:
    """Cria um renderer de avatares articulados"""
    return ArticulatedAvatarRenderer(screen_width, screen_height)
