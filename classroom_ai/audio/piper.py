from __future__ import annotations

import io
import threading
import wave
from pathlib import Path
from typing import Any, Callable

from classroom_ai.config import settings


class PiperUnavailableError(RuntimeError):
    """Raised when Piper or its configured voice is unavailable."""


class PiperSpeech:
    """Lazy, thread-safe adapter around Piper's local Python API."""

    def __init__(
        self,
        voice_path: Path = settings.piper_voice_path,
        *,
        vietnamese_voice_path: Path = settings.piper_vietnamese_voice_path,
        voice_factory: Callable[[str], Any] | None = None,
    ):
        self.voice_path = Path(voice_path)
        self.voice_paths = {
            "en-US": self.voice_path,
            "vi-VN": Path(vietnamese_voice_path),
        }
        self._voice_factory = voice_factory
        self._voices: dict[str, Any] = {}
        self._lock = threading.Lock()

    @property
    def config_path(self) -> Path:
        return self.voice_path.with_suffix(self.voice_path.suffix + ".json")

    def _load_voice(self, language: str) -> Any:
        if language in self._voices:
            return self._voices[language]
        voice_path = self.voice_paths.get(language)
        if voice_path is None:
            raise ValueError(f"Unsupported speech language: {language}")
        config_path = voice_path.with_suffix(voice_path.suffix + ".json")
        if not voice_path.is_file():
            raise PiperUnavailableError(
                f"Piper {language} voice not found: {voice_path}. "
                "Follow voices/README.md to download it."
            )
        if not config_path.is_file():
            raise PiperUnavailableError(
                f"Piper {language} voice config not found: {config_path}"
            )

        factory = self._voice_factory
        if factory is None:
            try:
                from piper import PiperVoice
            except ImportError as error:
                raise PiperUnavailableError(
                    "Piper is not installed. Run: pip install -r requirements-audio.txt"
                ) from error
            factory = PiperVoice.load

        voice = factory(str(voice_path))
        self._voices[language] = voice
        return voice

    def synthesize(self, text: str, language: str = "en-US") -> bytes:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Speech text cannot be blank")
        if len(clean_text) > 2000:
            raise ValueError("Speech text cannot exceed 2000 characters")

        with self._lock:
            voice = self._load_voice(language)
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                voice.synthesize_wav(clean_text, wav_file)
            return buffer.getvalue()
