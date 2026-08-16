"""Optional local speech components."""

from classroom_ai.audio.piper import PiperSpeech, PiperUnavailableError
from classroom_ai.audio.whisper_cpp import (
    TranscriptionError,
    TranscriptionUnavailableError,
    WhisperCppTranscriber,
)

__all__ = [
    "PiperSpeech",
    "PiperUnavailableError",
    "TranscriptionError",
    "TranscriptionUnavailableError",
    "WhisperCppTranscriber",
]
