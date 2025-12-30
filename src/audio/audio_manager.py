"""
BFF Dance - Sistema de Áudio
"""
import pygame
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

from ..config.settings import ASSETS_DIR, ALL_SOUNDS


@dataclass
class SoundEffect:
    """Efeito sonoro carregado"""
    name: str
    sound: pygame.mixer.Sound
    volume: float = 1.0


class AudioManager:
    """Gerenciador de áudio para música e efeitos sonoros"""

    def __init__(self):
        self._initialized = False
        self.sounds: Dict[str, SoundEffect] = {}
        self.music_volume = 0.7
        self.sfx_volume = 0.8
        self._music_playing = False

    def initialize(self) -> bool:
        """Inicializa o sistema de áudio"""
        try:
            # Inicializar mixer se não estiver
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

            # Configurar canais
            pygame.mixer.set_num_channels(16)

            # Carregar sons disponíveis
            self._load_sounds()

            self._initialized = True
            print(f"[INFO] Sistema de áudio inicializado")
            return True

        except Exception as e:
            print(f"[WARN] Áudio não disponível: {e}")
            return False

    def _load_sounds(self):
        """Carrega efeitos sonoros do diretório de assets"""
        sounds_dir = ASSETS_DIR / "sounds"

        if not sounds_dir.exists():
            sounds_dir.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Diretório de sons criado: {sounds_dir}")
            return

        # Procurar por arquivos de som
        for sound_name in ALL_SOUNDS:
            for ext in ['.wav', '.ogg', '.mp3']:
                sound_path = sounds_dir / f"{sound_name}{ext}"
                if sound_path.exists():
                    try:
                        sound = pygame.mixer.Sound(str(sound_path))
                        self.sounds[sound_name] = SoundEffect(
                            name=sound_name,
                            sound=sound,
                            volume=self.sfx_volume
                        )
                        print(f"[INFO] Som carregado: {sound_name}")
                    except Exception as e:
                        print(f"[WARN] Erro ao carregar {sound_name}: {e}")
                    break

    def play_sound(self, name: str, volume: Optional[float] = None):
        """
        Reproduz um efeito sonoro.

        Args:
            name: Nome do som (ex: 'boing', 'quack')
            volume: Volume opcional (0.0 a 1.0)
        """
        if not self._initialized:
            return

        if name in self.sounds:
            sfx = self.sounds[name]
            vol = volume if volume is not None else sfx.volume
            sfx.sound.set_volume(vol * self.sfx_volume)
            sfx.sound.play()
        else:
            # Som não carregado - apenas log, sem erro
            pass

    def play_random_sound(self, category: Optional[str] = None):
        """Reproduz um som aleatório"""
        import random

        if not self._initialized or not self.sounds:
            return

        available = list(self.sounds.keys())
        if available:
            sound_name = random.choice(available)
            self.play_sound(sound_name)

    def play_feedback_sound(self, feedback_type: str):
        """
        Reproduz som baseado no tipo de feedback.

        Args:
            feedback_type: 'perfect', 'good', 'ok', 'miss', 'easter_egg'
        """
        sound_map = {
            'perfect': 'wow',
            'good': 'sino',
            'ok': 'boing',
            'miss': 'buzina_palhaco',
            'easter_egg': 'airhorn',
        }

        sound_name = sound_map.get(feedback_type)
        if sound_name:
            self.play_sound(sound_name)

    def play_music(self, music_path: str, loops: int = -1):
        """
        Inicia reprodução de música de fundo.

        Args:
            music_path: Caminho para o arquivo de música
            loops: -1 para loop infinito
        """
        if not self._initialized:
            return

        try:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops)
            self._music_playing = True
        except Exception as e:
            print(f"[WARN] Erro ao reproduzir música: {e}")

    def stop_music(self):
        """Para a música de fundo"""
        if self._initialized:
            pygame.mixer.music.stop()
            self._music_playing = False

    def pause_music(self):
        """Pausa a música de fundo"""
        if self._initialized and self._music_playing:
            pygame.mixer.music.pause()

    def unpause_music(self):
        """Retoma a música de fundo"""
        if self._initialized:
            pygame.mixer.music.unpause()

    def set_music_volume(self, volume: float):
        """Define volume da música (0.0 a 1.0)"""
        self.music_volume = max(0.0, min(1.0, volume))
        if self._initialized:
            pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume: float):
        """Define volume dos efeitos sonoros (0.0 a 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))

    def cleanup(self):
        """Limpa recursos de áudio"""
        if self._initialized:
            pygame.mixer.stop()
            pygame.mixer.music.stop()
            self._initialized = False

    @property
    def is_music_playing(self) -> bool:
        """Verifica se há música tocando"""
        if self._initialized:
            return pygame.mixer.music.get_busy()
        return False
