from copy import deepcopy
from pathlib import Path
from typing import Any

from classroom_ai.config import settings
from classroom_ai.content import ImageCatalog, load_json


def load_tool_definition(path: Path) -> dict[str, Any]:
    definition = load_json(path)
    if definition.get("type") != "function":
        raise ValueError(f"Invalid tool definition in {path}")
    if not definition.get("function", {}).get("name"):
        raise ValueError(f"Tool definition has no function name: {path}")
    return definition


def build_tool_definitions(image_catalog: ImageCatalog) -> list[dict[str, Any]]:
    choices = load_tool_definition(settings.tool_definitions_dir / "show_choices.json")
    image = load_tool_definition(settings.tool_definitions_dir / "show_image.json")
    image = deepcopy(image)
    image["function"]["parameters"]["properties"]["image_id"]["enum"] = sorted(
        image_catalog
    )
    return [choices, image]
