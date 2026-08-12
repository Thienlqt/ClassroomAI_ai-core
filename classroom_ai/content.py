import json
from pathlib import Path
from typing import Any

from classroom_ai.config import PROJECT_ROOT, settings


ImageCatalog = dict[str, dict[str, str]]


def load_lesson(path: Path = settings.lesson_path) -> str:
    return path.read_text(encoding="utf-8")


def load_image_catalog(path: Path = settings.image_catalog_path) -> ImageCatalog:
    catalog: ImageCatalog = json.loads(path.read_text(encoding="utf-8"))
    images_dir = path.parent.resolve()

    for image_id, entry in catalog.items():
        if not isinstance(entry, dict) or "path" not in entry or "label" not in entry:
            raise ValueError(f"Invalid image catalog entry: {image_id}")

        asset_path = (PROJECT_ROOT / entry["path"]).resolve()
        if not asset_path.is_relative_to(images_dir):
            raise ValueError(f"Image '{image_id}' points outside the image directory")
        if not asset_path.is_file():
            raise FileNotFoundError(f"Image asset not found: {entry['path']}")

    return catalog


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value
