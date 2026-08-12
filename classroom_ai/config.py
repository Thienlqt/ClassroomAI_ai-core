import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    model_provider: str = os.getenv("CLASSROOM_MODEL_PROVIDER", "ollama")
    model: str = os.getenv("CLASSROOM_MODEL", "gemma4:e4b")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    openai_base_url: str = os.getenv(
        "CLASSROOM_OPENAI_BASE_URL", "http://127.0.0.1:8080/v1"
    )
    openai_api_key: str = os.getenv("CLASSROOM_OPENAI_API_KEY", "local-no-key")
    lesson_path: Path = PROJECT_ROOT / "lessons" / "animals.md"
    image_catalog_path: Path = PROJECT_ROOT / "assets" / "images" / "catalog.json"
    system_prompt_path: Path = PROJECT_ROOT / "prompts" / "english_teacher.txt"
    tool_definitions_dir: Path = PROJECT_ROOT / "tool_definitions"
    cors_origins: str = os.getenv("CLASSROOM_CORS_ORIGINS", "*")

    @property
    def images_dir(self) -> Path:
        return self.image_catalog_path.parent

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
