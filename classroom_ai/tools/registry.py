import json
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from classroom_ai.config import PROJECT_ROOT
from classroom_ai.content import ImageCatalog
from classroom_ai.schemas import (
    PendingToolCall,
    ShowChoicesArguments,
    ShowImageArguments,
    UiAction,
)
from classroom_ai.tools.definitions import build_tool_definitions


class ToolError(ValueError):
    pass


def tool_name(call: Any) -> str:
    function = getattr(call, "function", None)
    if function is not None:
        return getattr(function, "name", "")
    return call.get("function", {}).get("name", "")


def provider_tool_call_id(call: Any, fallback: str) -> str:
    call_id = getattr(call, "id", None)
    if call_id is None and isinstance(call, dict):
        call_id = call.get("id")
    return call_id or fallback


def tool_arguments(call: Any) -> dict[str, Any]:
    function = getattr(call, "function", None)
    arguments = (
        getattr(function, "arguments", {})
        if function is not None
        else call.get("function", {}).get("arguments", {})
    )
    if isinstance(arguments, str):
        return json.loads(arguments)
    if not isinstance(arguments, dict):
        raise ToolError("Tool arguments must be an object")
    return arguments


class ToolRegistry:
    def __init__(self, image_catalog: ImageCatalog):
        self.image_catalog = image_catalog
        self.definitions = build_tool_definitions(image_catalog)

    def create_action(self, call: Any) -> tuple[UiAction, PendingToolCall]:
        name = tool_name(call)
        call_id = str(uuid4())

        try:
            raw_arguments = tool_arguments(call)
            if name == "show_choices":
                arguments = ShowChoicesArguments.model_validate(raw_arguments)
                action = UiAction(
                    call_id=call_id,
                    type="ui.show_choices",
                    payload={
                        "question": arguments.question,
                        "choices": arguments.choices,
                    },
                )
            elif name == "show_image":
                arguments = ShowImageArguments.model_validate(raw_arguments)
                entry = self.image_catalog.get(arguments.image_id)
                if entry is None:
                    raise ToolError(f"Unknown image_id: {arguments.image_id}")
                asset_path = (PROJECT_ROOT / entry["path"]).resolve()
                if not asset_path.is_file():
                    raise ToolError(f"Image asset is unavailable: {arguments.image_id}")
                action = UiAction(
                    call_id=call_id,
                    type="ui.show_image",
                    payload={
                        "image_id": arguments.image_id,
                        "caption": arguments.caption,
                        "image_url": f"/assets/images/{asset_path.name}",
                    },
                )
            else:
                raise ToolError(f"Unknown tool: {name}")
        except (json.JSONDecodeError, ValidationError) as error:
            raise ToolError(f"Invalid {name} arguments: {error}") from error

        pending = PendingToolCall(
            call_id=call_id,
            provider_call_id=provider_tool_call_id(call, call_id),
            name=name,
            arguments=raw_arguments,
        )
        return action, pending

    def resolve_result(
        self,
        pending: PendingToolCall,
        app_result: dict[str, Any],
    ) -> dict[str, Any]:
        if pending.name == "show_choices":
            arguments = ShowChoicesArguments.model_validate(pending.arguments)
            selected = app_result.get("selected")
            if selected not in arguments.choices:
                raise ToolError("selected must exactly match one of the choices")
            return {
                "selected": selected,
                "correct": selected.strip().casefold()
                == arguments.correct_answer.strip().casefold(),
            }

        if pending.name == "show_image":
            success = app_result.get("success")
            if not isinstance(success, bool):
                raise ToolError("show_image result requires a boolean success field")
            arguments = ShowImageArguments.model_validate(pending.arguments)
            return {"success": success, "image_id": arguments.image_id}

        raise ToolError(f"Unknown pending tool: {pending.name}")
