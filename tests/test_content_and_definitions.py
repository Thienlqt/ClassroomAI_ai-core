import json

import pytest

from classroom_ai.content import load_image_catalog
from classroom_ai.prompts import build_system_prompt
from classroom_ai.tools.definitions import build_tool_definitions, load_tool_definition


def test_system_prompt_is_loaded_from_template_file(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Lesson={{LESSON}}\nImages={{IMAGE_IDS}}", encoding="utf-8")

    prompt = build_system_prompt(
        "Animals lesson",
        {"lion": {}, "dog": {}},
        path=prompt_path,
    )

    assert prompt == "Lesson=Animals lesson\nImages=dog, lion"


def test_system_prompt_requires_runtime_placeholders(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("No placeholders", encoding="utf-8")

    with pytest.raises(ValueError, match="missing placeholders"):
        build_system_prompt("lesson", {}, path=prompt_path)


def test_tool_definitions_come_from_json_and_image_ids_are_dynamic():
    choices, image = build_tool_definitions(load_image_catalog())

    assert choices["function"]["name"] == "show_choices"
    image_id = image["function"]["parameters"]["properties"]["image_id"]
    assert image_id["enum"] == ["dog", "eagle", "fish", "lion"]


def test_tool_definition_loader_rejects_non_function_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"type": "not-a-function"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid tool definition"):
        load_tool_definition(path)
