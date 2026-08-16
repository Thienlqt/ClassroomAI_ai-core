import os
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    model_provider: str = field(
        default_factory=lambda: os.getenv("CLASSROOM_MODEL_PROVIDER", "llama_cpp")
    )
    model: str = field(
        default_factory=lambda: os.getenv("CLASSROOM_MODEL", "gemma4-e4b")
    )
    ollama_host: str = field(
        default_factory=lambda: os.getenv(
            "OLLAMA_HOST", "http://127.0.0.1:11434"
        )
    )
    openai_base_url: str = field(
        default_factory=lambda: os.getenv(
            "CLASSROOM_OPENAI_BASE_URL", "http://127.0.0.1:8080/v1"
        )
    )
    openai_api_key: str = field(
        default_factory=lambda: os.getenv(
            "CLASSROOM_OPENAI_API_KEY", "local-no-key"
        )
    )
    lesson_path: Path = PROJECT_ROOT / "lessons" / "animals.md"
    image_catalog_path: Path = PROJECT_ROOT / "assets" / "images" / "catalog.json"
    system_prompt_path: Path = PROJECT_ROOT / "prompts" / "english_teacher.txt"
    tool_definitions_dir: Path = PROJECT_ROOT / "tool_definitions"
    frontend_dir: Path = PROJECT_ROOT / "frontend" / "bundle"
    avatar_dir: Path = field(
        default_factory=lambda: _project_path(
            os.getenv("CLASSROOM_AVATAR_DIR", "models/avatar")
        )
    )
    piper_voice_path: Path = field(
        default_factory=lambda: _project_path(
            os.getenv(
                "CLASSROOM_PIPER_VOICE",
                "voices/en_US-lessac-medium.onnx",
            )
        )
    )
    piper_vietnamese_voice_path: Path = field(
        default_factory=lambda: _project_path(
            os.getenv(
                "CLASSROOM_PIPER_VIETNAMESE_VOICE",
                "voices/vi_VN-vais1000-medium.onnx",
            )
        )
    )
    whisper_model_path: Path = field(
        default_factory=lambda: _project_path(
            os.getenv(
                "CLASSROOM_WHISPER_MODEL",
                "models/speech/ggml-small.bin",
            )
        )
    )
    whisper_language: str = field(
        default_factory=lambda: os.getenv("CLASSROOM_WHISPER_LANGUAGE", "auto")
    )
    whisper_use_gpu: bool = field(
        default_factory=lambda: os.getenv("CLASSROOM_WHISPER_USE_GPU", "0")
        .strip()
        .casefold()
        in {"1", "true", "yes", "on"}
    )
    whisper_command: str = field(
        default_factory=lambda: os.getenv("CLASSROOM_WHISPER_COMMAND", "whisper-cli")
    )
    ffmpeg_command: str = field(
        default_factory=lambda: os.getenv("CLASSROOM_FFMPEG_COMMAND", "ffmpeg")
    )
    whisper_threads: int = field(
        default_factory=lambda: int(os.getenv("CLASSROOM_WHISPER_THREADS", "4"))
    )
    face_detector_model_path: Path = field(
        default_factory=lambda: _project_path(
            os.getenv(
                "CLASSROOM_FACE_DETECTOR_MODEL",
                "models/vision/face_detection_yunet_2023mar.onnx",
            )
        )
    )
    face_recognizer_model_path: Path = field(
        default_factory=lambda: _project_path(
            os.getenv(
                "CLASSROOM_FACE_RECOGNIZER_MODEL",
                "models/vision/face_recognition_sface_2021dec.onnx",
            )
        )
    )
    face_cosine_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("CLASSROOM_FACE_COSINE_THRESHOLD", "0.45")
        )
    )
    face_database_path: Path = field(
        default_factory=lambda: _project_path(
            os.getenv("CLASSROOM_FACE_DATABASE", "data/faces.sqlite3")
        )
    )
    cors_origins: str = field(
        default_factory=lambda: os.getenv(
            "CLASSROOM_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
    )

    @property
    def images_dir(self) -> Path:
        return self.image_catalog_path.parent

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
