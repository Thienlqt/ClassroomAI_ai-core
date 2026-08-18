from pathlib import Path

from classroom_ai.config import settings
from classroom_ai.content import ImageCatalog


def build_system_prompt(
    lesson: str,
    image_catalog: ImageCatalog,
    path: Path = settings.system_prompt_path,
) -> str:
    template = path.read_text(encoding="utf-8")
    replacements = {
        "{{LESSON}}": lesson,
        "{{IMAGE_IDS}}": ", ".join(sorted(image_catalog)),
    }

    missing = [placeholder for placeholder in replacements if placeholder not in template]
    if missing:
        raise ValueError(f"System prompt is missing placeholders: {', '.join(missing)}")

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    return template.strip()
