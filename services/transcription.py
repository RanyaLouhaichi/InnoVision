import whisper # type: ignore
import os
from typing import Optional

class TranscriptionService:
    def __init__(self, model_name: str = "base"):
        try:
            self.model = whisper.load_model(model_name)
            print(f"Loaded Whisper model: {model_name}")
        except Exception as e:
            print(f"Error loading Whisper model ({model_name}): {e}")
            try:
                print("Attempting to load 'tiny' Whisper model as a fallback.")
                self.model = whisper.load_model("tiny")
                print("Loaded Whisper model: tiny (fallback)")
            except Exception as e_fallback:
                print(f"Error loading fallback 'tiny' Whisper model: {e_fallback}")
                self.model = None
                raise RuntimeError(f"Could not load Whisper model '{model_name}' or fallback 'tiny'. Please check your Whisper installation and model availability.") from e_fallback

    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        if not self.model:
            print("Whisper model not loaded. Cannot transcribe.")
            return None
        try:
            if not os.path.exists(audio_path):
                print(f"Audio file not found: {audio_path}")
                return None
            result = self.model.transcribe(
                audio_path,
                language="ar",
                fp16=False
            )
            text = result["text"].strip()
            print(f"Transcription: {text}")
            return text
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    def detect_language(self, audio_path: str) -> str:
        if not self.model:
            print("Whisper model not loaded. Cannot detect language.")
            return "unknown"
        try:
            if not os.path.exists(audio_path):
                print(f"Audio file not found for language detection: {audio_path}")
                return "unknown"
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            _, probs = self.model.detect_language(mel)
            detected_lang = max(probs, key=probs.get)
            print(f"Detected language: {detected_lang}")
            return detected_lang
        except Exception as e:
            print(f"Language detection error: {e}")
            return "unknown"