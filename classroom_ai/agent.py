import json
from typing import Any

from classroom_ai.content import ImageCatalog, load_image_catalog, load_lesson
from classroom_ai.model import ModelGateway, create_model_gateway
from classroom_ai.policies import refers_to_unavailable_visual
from classroom_ai.prompts import build_system_prompt
from classroom_ai.schemas import AgentOutput, PendingToolCall
from classroom_ai.tools.registry import (
    ToolError,
    ToolRegistry,
    provider_tool_call_id,
    tool_name,
)


MAX_TOOL_ATTEMPTS = 2
MAX_FEEDBACK_ATTEMPTS = 2


class AgentStateError(RuntimeError):
    pass


def _message_tool_calls(message: Any) -> list[Any]:
    calls = getattr(message, "tool_calls", None)
    if calls is not None:
        return calls or []
    if isinstance(message, dict):
        return message.get("tool_calls") or []
    return []


def _message_content(message: Any) -> str:
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    return (content or "").strip()


class ClassroomAgent:
    """Model orchestration independent of terminal, HTTP, or UI rendering."""

    def __init__(
        self,
        model: ModelGateway | None = None,
        image_catalog: ImageCatalog | None = None,
        lesson: str | None = None,
    ):
        self.image_catalog = image_catalog or load_image_catalog()
        self.registry = ToolRegistry(self.image_catalog)
        self.model = model or create_model_gateway()
        self.system_prompt = build_system_prompt(
            lesson or load_lesson(),
            self.image_catalog,
        )

    def new_conversation(self) -> list[Any]:
        return [{"role": "system", "content": self.system_prompt}]

    def submit_message(
        self,
        messages: list[Any],
        student_message: str,
    ) -> tuple[AgentOutput, PendingToolCall | None]:
        if not student_message.strip():
            raise ValueError("Student message cannot be blank")

        messages.append({"role": "user", "content": student_message.strip()})

        for attempt in range(MAX_TOOL_ATTEMPTS):
            model_message = self.model.chat(messages, tools=self.registry.definitions)
            messages.append(model_message)
            calls = _message_tool_calls(model_message)

            if not calls:
                speech = _message_content(model_message)
                if not speech:
                    raise AgentStateError("Model returned neither speech nor a tool call")
                return AgentOutput(type="speech", speech=speech), None

            if len(calls) != 1:
                raise ToolError("Only one classroom tool call is allowed per turn")

            try:
                action, pending = self.registry.create_action(calls[0])
                return AgentOutput(type="action", action=action), pending
            except ToolError as error:
                if attempt == MAX_TOOL_ATTEMPTS - 1:
                    raise
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name(calls[0]),
                        "tool_call_id": provider_tool_call_id(
                            calls[0], f"repair-{attempt}"
                        ),
                        "content": json.dumps(
                            {
                                "error": str(error),
                                "instruction": (
                                    "Correct the arguments and call exactly one tool again."
                                ),
                            }
                        ),
                    }
                )

        raise AgentStateError("Tool repair loop ended unexpectedly")

    def submit_action_result(
        self,
        messages: list[Any],
        pending: PendingToolCall,
        app_result: dict[str, Any],
    ) -> AgentOutput:
        observation = self.registry.resolve_result(pending, app_result)
        messages.append(
            {
                "role": "tool",
                "tool_name": pending.name,
                "tool_call_id": pending.provider_call_id,
                "content": json.dumps(observation),
            }
        )

        # Tools are intentionally omitted: Gemma must respond to this observation
        # before it can request another classroom action.
        if pending.name == "show_choices":
            ui_state = (
                "CURRENT UI STATE: The multiple-choice activity is finished. No image "
                "was displayed. Give feedback about the answer only. Do not mention, "
                "describe, or ask the student to look at a picture or screen image."
            )
        else:
            ui_state = (
                "CURRENT UI STATE: The requested image display result is included in "
                "the tool observation. Refer to the image only if success is true."
            )

        visual_is_available = pending.name == "show_image" and observation["success"]
        feedback_context = messages + [{"role": "system", "content": ui_state}]

        for attempt in range(MAX_FEEDBACK_ATTEMPTS):
            model_message = self.model.chat(feedback_context)

            if _message_tool_calls(model_message):
                raise AgentStateError("Model requested a tool while tools were disabled")

            speech = _message_content(model_message)
            if not speech:
                raise AgentStateError("Model returned empty feedback after the tool result")

            if not visual_is_available and refers_to_unavailable_visual(speech):
                if attempt == MAX_FEEDBACK_ATTEMPTS - 1:
                    raise AgentStateError(
                        "Model repeatedly referred to an image that was not displayed"
                    )
                feedback_context = feedback_context + [
                    model_message,
                    {
                        "role": "system",
                        "content": (
                            "POLICY CORRECTION: Your draft referred to visible content, "
                            "but no image was displayed. Rewrite it using verbal teaching "
                            "only. Do not use 'look at', 'picture', 'image', or 'screen'."
                        ),
                    },
                ]
                continue

            messages.append(model_message)
            return AgentOutput(type="speech", speech=speech)

        raise AgentStateError("Feedback policy loop ended unexpectedly")
