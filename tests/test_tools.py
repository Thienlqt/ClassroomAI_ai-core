import pytest
from pydantic import ValidationError

from classroom_ai.content import load_image_catalog
from classroom_ai.schemas import ShowChoicesArguments
from classroom_ai.tools.registry import ToolError, ToolRegistry
from tests.helpers import tool_call


def test_choices_action_hides_correct_answer_from_app():
    registry = ToolRegistry(load_image_catalog())
    action, pending = registry.create_action(
        tool_call(
            "show_choices",
            {
                "question": "Which animal can fly?",
                "choices": ["Eagle", "Fish", "Dog"],
                "correct_answer": "Eagle",
            },
        )
    )

    assert action.type == "ui.show_choices"
    assert action.payload == {
        "question": "Which animal can fly?",
        "choices": ["Eagle", "Fish", "Dog"],
    }
    assert "correct_answer" not in action.payload
    assert registry.resolve_result(pending, {"selected": "Eagle"}) == {
        "selected": "Eagle",
        "correct": True,
    }


def test_choices_schema_rejects_answer_outside_choices():
    with pytest.raises(ValidationError, match="correct_answer must be one of choices"):
        ShowChoicesArguments(
            question="Which animal can fly?",
            choices=["Eagle", "Fish", "Dog"],
            correct_answer="Bird",
        )


def test_image_action_contains_frontend_url():
    registry = ToolRegistry(load_image_catalog())
    action, pending = registry.create_action(
        tool_call("show_image", {"image_id": "lion", "caption": "Lion"})
    )

    assert action.type == "ui.show_image"
    assert action.payload == {
        "image_id": "lion",
        "caption": "Lion",
        "image_url": "/assets/images/lion.png",
    }
    assert registry.resolve_result(pending, {"success": True}) == {
        "success": True,
        "image_id": "lion",
    }


def test_unknown_image_is_rejected():
    registry = ToolRegistry(load_image_catalog())
    with pytest.raises(ToolError, match="Unknown image_id: tiger"):
        registry.create_action(
            tool_call("show_image", {"image_id": "tiger", "caption": "Tiger"})
        )


def test_app_must_return_an_exact_choice():
    registry = ToolRegistry(load_image_catalog())
    _, pending = registry.create_action(
        tool_call(
            "show_choices",
            {
                "question": "Which animal can fly?",
                "choices": ["Eagle", "Fish"],
                "correct_answer": "Eagle",
            },
        )
    )

    with pytest.raises(ToolError, match="exactly match"):
        registry.resolve_result(pending, {"selected": "Bird"})
