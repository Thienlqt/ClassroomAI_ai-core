from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Callable, Sequence

from classroom_ai.config import settings


class TranscriptionUnavailableError(RuntimeError):
    """Raised when the local speech-to-text runtime is not ready."""


class TranscriptionError(RuntimeError):
    """Raised when uploaded audio cannot be converted or transcribed."""


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
CommandLookup = Callable[[str], str | None]


class WhisperCppTranscriber:
    """Small, serialized adapter around the local whisper.cpp command line."""

    def __init__(
        self,
        model_path: Path = settings.whisper_model_path,
        *,
        whisper_command: str = settings.whisper_command,
        ffmpeg_command: str = settings.ffmpeg_command,
        language: str = settings.whisper_language,
        use_gpu: bool = settings.whisper_use_gpu,
        threads: int = settings.whisper_threads,
        runner: CommandRunner = subprocess.run,
        command_lookup: CommandLookup = shutil.which,
    ):
        self.model_path = Path(model_path)
        self.whisper_command = whisper_command
        self.ffmpeg_command = ffmpeg_command
        self.language = language.strip() or "auto"
        self.use_gpu = use_gpu
        self.threads = threads
        self._runner = runner
        self._command_lookup = command_lookup
        self._lock = threading.Lock()

    def _validate(self) -> None:
        if not self.model_path.is_file():
            raise TranscriptionUnavailableError(
                f"Whisper model not found: {self.model_path}. "
                "Follow models/README.md to download it."
            )
        if self._command_lookup(self.whisper_command) is None:
            raise TranscriptionUnavailableError(
                f"whisper.cpp command not found: {self.whisper_command}"
            )
        if self._command_lookup(self.ffmpeg_command) is None:
            raise TranscriptionUnavailableError(
                f"FFmpeg command not found: {self.ffmpeg_command}"
            )
        if self.threads < 1:
            raise TranscriptionUnavailableError(
                "CLASSROOM_WHISPER_THREADS must be at least 1."
            )

    @staticmethod
    def _run(
        runner: CommandRunner,
        command: Sequence[str],
        *,
        failure_message: str,
    ) -> None:
        try:
            runner(
                list(command),
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise TranscriptionError(failure_message) from error

    def transcribe(self, audio: bytes) -> str:
        if not audio:
            raise ValueError("Audio file cannot be empty.")

        self._validate()
        with self._lock, tempfile.TemporaryDirectory(prefix="classroom-stt-") as temp:
            temp_dir = Path(temp)
            uploaded_path = temp_dir / "uploaded-audio"
            wav_path = temp_dir / "normalized.wav"
            output_base = temp_dir / "transcript"
            transcript_path = output_base.with_suffix(".txt")
            uploaded_path.write_bytes(audio)

            self._run(
                self._runner,
                [
                    self.ffmpeg_command,
                    "-nostdin",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(uploaded_path),
                    "-t",
                    "60",
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    str(wav_path),
                ],
                failure_message="FFmpeg could not decode the uploaded audio.",
            )
            whisper_command = [
                self.whisper_command,
                "--model",
                str(self.model_path),
                "--file",
                str(wav_path),
                "--language",
                self.language,
                "--threads",
                str(self.threads),
            ]
            if not self.use_gpu:
                whisper_command.append("--no-gpu")
            whisper_command.extend(
                [
                    "--output-txt",
                    "--output-file",
                    str(output_base),
                    "--no-timestamps",
                    "--no-prints",
                ]
            )
            self._run(
                self._runner,
                whisper_command,
                failure_message="whisper.cpp could not transcribe the audio.",
            )

            if not transcript_path.is_file():
                raise TranscriptionError("whisper.cpp did not create a transcript.")
            transcript = transcript_path.read_text(encoding="utf-8").strip()
            if not transcript:
                raise TranscriptionError("No speech was detected in the audio.")
            return transcript
