import io
import subprocess
import wave
from pathlib import Path
import pytest

from classroom_ai.audio.piper import PiperSpeech, PiperUnavailableError
from classroom_ai.audio.whisper_cpp import (
    TranscriptionUnavailableError,
    WhisperCppTranscriber,
)
from classroom_ai.vision.base import FaceRecognitionUnavailableError
from classroom_ai.vision.face_recognition import OpenCVFaceRecognition
from classroom_ai.vision.face_store import FaceEmbeddingStore


class FakePiperVoice:
    def synthesize_wav(self, text, wav_file):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16_000)
        wav_file.writeframes(b"\x00\x00" * len(text))


def test_piper_synthesizes_wav_with_lazy_injected_voice(tmp_path):
    model_path = tmp_path / "voice.onnx"
    model_path.write_bytes(b"model")
    model_path.with_suffix(".onnx.json").write_text("{}")
    loaded_paths = []

    speech = PiperSpeech(
        model_path,
        voice_factory=lambda path: loaded_paths.append(path) or FakePiperVoice(),
    )
    audio = speech.synthesize("Hello")

    assert loaded_paths == [str(model_path)]
    with wave.open(io.BytesIO(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 16_000
        assert wav_file.getnframes() == 5


def test_piper_reports_missing_voice_before_importing_package(tmp_path):
    speech = PiperSpeech(tmp_path / "missing.onnx")

    with pytest.raises(PiperUnavailableError, match="Voice not found|voice not found"):
        speech.synthesize("Hello")


def test_whisper_cpp_converts_and_transcribes_uploaded_audio(tmp_path):
    model_path = tmp_path / "whisper.bin"
    model_path.write_bytes(b"model")
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "ffmpeg":
            Path(command[-1]).write_bytes(b"normalized-wav")
        else:
            output_base = Path(command[command.index("--output-file") + 1])
            output_base.with_suffix(".txt").write_text(
                " Can an eagle fly?\n", encoding="utf-8"
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    transcriber = WhisperCppTranscriber(
        model_path,
        threads=6,
        runner=fake_run,
        command_lookup=lambda command: f"/fake/{command}",
    )

    text = transcriber.transcribe(b"browser-audio")

    assert text == "Can an eagle fly?"
    assert commands[0][0] == "ffmpeg"
    assert commands[1][0] == "whisper-cli"
    assert commands[1][commands[1].index("--language") + 1] == "auto"
    assert commands[1][commands[1].index("--threads") + 1] == "6"
    assert "--no-gpu" in commands[1]


def test_whisper_cpp_reports_missing_model(tmp_path):
    transcriber = WhisperCppTranscriber(
        tmp_path / "missing.bin",
        command_lookup=lambda command: f"/fake/{command}",
    )

    with pytest.raises(TranscriptionUnavailableError, match="model not found"):
        transcriber.transcribe(b"audio")


def test_face_recognition_reports_missing_models_before_importing_opencv(tmp_path):
    recognition = OpenCVFaceRecognition(
        detector_path=tmp_path / "yunet.onnx",
        recognizer_path=tmp_path / "sface.onnx",
    )

    with pytest.raises(FaceRecognitionUnavailableError, match="model not found"):
        recognition.recognize(b"image")


def test_face_recognition_normalizes_and_clamps_detection_bounds():
    bounds = OpenCVFaceRecognition._bounds(
        [-10, 10, 60, 40], width=100, height=100
    )

    assert bounds is not None
    assert bounds.model_dump() == {
        "x_min": 0.0,
        "y_min": 0.1,
        "x_max": 0.5,
        "y_max": 0.5,
    }


def test_face_store_uses_same_model_cosine_matching_and_deletion(tmp_path):
    store = FaceEmbeddingStore(tmp_path / "faces.sqlite3")
    store.enroll(
        subject_id="student-1",
        display_name="Student One",
        embedding=[1.0, 0.0, 0.0],
        model_id="encoder@1",
        consent_reference="consent-1",
    )
    store.enroll(
        subject_id="student-2",
        display_name="Student Two",
        embedding=[0.0, 1.0, 0.0],
        model_id="encoder@1",
        consent_reference="consent-2",
    )
    store.enroll(
        subject_id="student-3",
        display_name="Wrong Encoder",
        embedding=[1.0, 0.0, 0.0],
        model_id="encoder@2",
        consent_reference="consent-3",
    )

    matches = store.match(
        [0.99, 0.01, 0.0], model_id="encoder@1", threshold=0.8
    )

    assert [match.subject_id for match in matches] == ["student-1"]
    assert matches[0].similarity > 0.99
    assert len(store.list_subjects()) == 3
    assert store.delete_subject("student-1") is True
    assert store.match([1, 0, 0], model_id="encoder@1", threshold=0.8) == []


def test_face_store_requires_a_consent_reference(tmp_path):
    store = FaceEmbeddingStore(tmp_path / "faces.sqlite3")

    with pytest.raises(ValueError, match="consent_reference"):
        store.enroll(
            subject_id="student-1",
            display_name="Student One",
            embedding=[1.0, 0.0],
            model_id="encoder@1",
            consent_reference="",
        )
