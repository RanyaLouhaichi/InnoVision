from gtts import gTTS # type: ignore
import pygame
import io
import tempfile
import os
from typing import Optional
from pathlib import Path

class TTSService:
    # Define STATIC_AUDIO_DIR as a class attribute
    STATIC_AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "generated_audio"
    
    def __init__(self):
        # Ensure the directory exists
        os.makedirs(self.STATIC_AUDIO_DIR, exist_ok=True)
        
        try:
            pygame.mixer.init()
            self._pygame_initialized = True
        except Exception as e:
            print(f"Pygame mixer initialization failed: {e}. Local playback (speak_text) might not work.")
            self._pygame_initialized = False

    def speak_text(self, text: str, lang: str = "fr") -> bool:
        if not self._pygame_initialized:
            print("Pygame not initialized. Cannot play audio directly.")
            return False
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as tmp_file:
                tts.save(tmp_file.name)
                pygame.mixer.music.load(tmp_file.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
            return True
        except Exception as e:
            print(f"TTS local playback error: {e}")
            return False

    def generate_audio_file(self, text: str, filename_prefix: str, lang: str = "fr") -> Optional[str]:
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            output_filename = f"{filename_prefix}_{lang}.mp3"
            output_path = self.STATIC_AUDIO_DIR / output_filename
            tts.save(str(output_path))
            print(f"Generated audio file: {output_path}")
            return os.path.join("generated_audio", output_filename) 
        except Exception as e:
            print(f"Audio generation error: {e}")
            return None