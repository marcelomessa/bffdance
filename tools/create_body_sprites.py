#!/usr/bin/env python3
"""
Cria sprites de partes do corpo estilizadas para os avatares
Estilo cartoon colorido que combina com os animais Kenney
"""
import pygame
import os
import math

# Diretório de saída
OUTPUT_DIR = "/home/admin/projects/bffdance/assets/sprites/body_parts"

# Cores base para cada personagem (podem ser tintadas depois)
COLORS = {
    'panda': {'primary': (40, 40, 40), 'secondary': (255, 255, 255), 'accent': (255, 150, 150)},
    'monkey': {'primary': (139, 90, 43), 'secondary': (222, 184, 135), 'accent': (255, 200, 150)},
    'penguin': {'primary': (30, 30, 30), 'secondary': (255, 255, 255), 'accent': (255, 165, 0)},
    'rabbit': {'primary': (255, 255, 255), 'secondary': (255, 200, 200), 'accent': (255, 150, 180)},
    'parrot': {'primary': (50, 200, 50), 'secondary': (255, 50, 50), 'accent': (255, 255, 0)},
    'elephant': {'primary': (150, 150, 170), 'secondary': (180, 180, 200), 'accent': (255, 180, 200)},
    'giraffe': {'primary': (255, 200, 100), 'secondary': (180, 120, 60), 'accent': (255, 220, 150)},
    'hippo': {'primary': (150, 130, 160), 'secondary': (180, 160, 190), 'accent': (255, 180, 200)},
    'pig': {'primary': (255, 180, 180), 'secondary': (255, 200, 200), 'accent': (255, 150, 150)},
    'snake': {'primary': (100, 180, 100), 'secondary': (150, 220, 150), 'accent': (255, 255, 100)},
    'frog': {'primary': (100, 200, 100), 'secondary': (150, 255, 150), 'accent': (255, 100, 100)},
    'capybara': {'primary': (139, 90, 60), 'secondary': (180, 130, 90), 'accent': (255, 200, 150)},
}


def create_rounded_rect_surface(width, height, color, radius=10, outline_color=None, outline_width=3):
    """Cria superfície com retângulo arredondado"""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # Desenhar outline primeiro se existir
    if outline_color:
        pygame.draw.rect(surface, outline_color, (0, 0, width, height), border_radius=radius)
        # Desenhar interior menor
        inner_rect = (outline_width, outline_width,
                      width - outline_width*2, height - outline_width*2)
        pygame.draw.rect(surface, color, inner_rect, border_radius=max(1, radius-outline_width))
    else:
        pygame.draw.rect(surface, color, (0, 0, width, height), border_radius=radius)

    return surface


def create_ellipse_surface(width, height, color, outline_color=None, outline_width=3):
    """Cria superfície com elipse"""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    if outline_color:
        pygame.draw.ellipse(surface, outline_color, (0, 0, width, height))
        inner_rect = (outline_width, outline_width,
                      width - outline_width*2, height - outline_width*2)
        pygame.draw.ellipse(surface, color, inner_rect)
    else:
        pygame.draw.ellipse(surface, color, (0, 0, width, height))

    return surface


def add_highlight(surface, intensity=0.3):
    """Adiciona highlight/brilho sutil"""
    width, height = surface.get_size()
    highlight = pygame.Surface((width, height), pygame.SRCALPHA)

    # Gradiente de brilho do topo
    for y in range(height // 3):
        alpha = int(255 * intensity * (1 - y / (height // 3)))
        pygame.draw.line(highlight, (255, 255, 255, alpha), (0, y), (width, y))

    surface.blit(highlight, (0, 0))
    return surface


def create_body_part(part_type, colors, size):
    """
    Cria uma parte do corpo específica

    part_type: 'torso', 'upper_arm', 'lower_arm', 'hand', 'upper_leg', 'lower_leg', 'foot'
    colors: dict com 'primary', 'secondary', 'accent'
    size: tamanho base (será ajustado por parte)
    """
    outline_color = (30, 30, 30)
    outline_width = 3

    if part_type == 'torso':
        # Tronco oval/retangular arredondado
        width, height = int(size * 0.8), int(size * 1.0)
        surface = create_rounded_rect_surface(
            width, height, colors['primary'],
            radius=width//3, outline_color=outline_color, outline_width=outline_width
        )
        # Adicionar barriga/peito secundário
        belly_w, belly_h = int(width * 0.6), int(height * 0.5)
        belly = create_ellipse_surface(belly_w, belly_h, colors['secondary'])
        surface.blit(belly, ((width - belly_w)//2, int(height * 0.3)))

    elif part_type == 'upper_arm':
        # Braço superior - cápsula/retângulo arredondado
        width, height = int(size * 0.25), int(size * 0.4)
        surface = create_rounded_rect_surface(
            width, height, colors['primary'],
            radius=width//2, outline_color=outline_color, outline_width=outline_width
        )

    elif part_type == 'lower_arm':
        # Antebraço - ligeiramente mais fino
        width, height = int(size * 0.22), int(size * 0.35)
        surface = create_rounded_rect_surface(
            width, height, colors['primary'],
            radius=width//2, outline_color=outline_color, outline_width=outline_width
        )

    elif part_type == 'hand':
        # Mão - circular/oval
        width, height = int(size * 0.2), int(size * 0.2)
        surface = create_ellipse_surface(
            width, height, colors['secondary'],
            outline_color=outline_color, outline_width=outline_width
        )

    elif part_type == 'upper_leg':
        # Coxa - mais grossa
        width, height = int(size * 0.3), int(size * 0.45)
        surface = create_rounded_rect_surface(
            width, height, colors['primary'],
            radius=width//2, outline_color=outline_color, outline_width=outline_width
        )

    elif part_type == 'lower_leg':
        # Canela - mais fina
        width, height = int(size * 0.25), int(size * 0.4)
        surface = create_rounded_rect_surface(
            width, height, colors['primary'],
            radius=width//2, outline_color=outline_color, outline_width=outline_width
        )

    elif part_type == 'foot':
        # Pé - oval horizontal
        width, height = int(size * 0.3), int(size * 0.15)
        surface = create_ellipse_surface(
            width, height, colors['secondary'],
            outline_color=outline_color, outline_width=outline_width
        )

    else:
        # Fallback - círculo
        width = height = int(size * 0.3)
        surface = create_ellipse_surface(
            width, height, colors['primary'],
            outline_color=outline_color, outline_width=outline_width
        )

    # Adicionar highlight sutil
    add_highlight(surface, 0.2)

    return surface


def create_joint(size, color):
    """Cria uma articulação (círculo para conectar partes)"""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surface, (30, 30, 30), (size//2, size//2), size//2)
    pygame.draw.circle(surface, color, (size//2, size//2), size//2 - 2)
    return surface


def create_character_parts(name, colors, base_size=100):
    """Cria todas as partes para um personagem"""
    parts = {}

    # Partes do corpo
    part_types = ['torso', 'upper_arm', 'lower_arm', 'hand', 'upper_leg', 'lower_leg', 'foot']

    for part_type in part_types:
        parts[part_type] = create_body_part(part_type, colors, base_size)

    # Articulações
    joint_size = int(base_size * 0.15)
    parts['joint'] = create_joint(joint_size, colors['primary'])
    parts['joint_light'] = create_joint(joint_size, colors['secondary'])

    return parts


def save_character_parts(name, parts, output_dir):
    """Salva as partes do personagem em disco"""
    char_dir = os.path.join(output_dir, name)
    os.makedirs(char_dir, exist_ok=True)

    for part_name, surface in parts.items():
        filepath = os.path.join(char_dir, f"{part_name}.png")
        pygame.image.save(surface, filepath)
        print(f"  Saved: {filepath}")


def create_all_characters():
    """Cria sprites para todos os personagens"""
    pygame.init()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=== Criando sprites de partes do corpo ===\n")

    for name, colors in COLORS.items():
        print(f"Criando: {name}")
        parts = create_character_parts(name, colors, base_size=120)
        save_character_parts(name, parts, OUTPUT_DIR)
        print()

    print(f"\nTodos os sprites salvos em: {OUTPUT_DIR}")
    pygame.quit()


if __name__ == "__main__":
    create_all_characters()
