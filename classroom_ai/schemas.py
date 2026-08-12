from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShowChoicesArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=200)
    choices: list[str] = Field(min_length=2, max_length=4)
    correct_answer: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_choices(self) -> "ShowChoicesArguments":
        normalized = [choice.strip().casefold() for choice in self.choices]
        if any(not choice.strip() for choice in self.choices):
            raise ValueError("choices cannot contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("choices must be unique")
        if self.correct_answer.strip().casefold() not in normalized:
            raise ValueError("correct_answer must be one of choices")
        return self


class ShowImageArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id: str = Field(pattern=r"^[a-z0-9_-]+$", min_length=1, max_length=50)
    caption: str = Field(min_length=1, max_length=100)


class UiAction(BaseModel):
    call_id: str
    type: Literal["ui.show_choices", "ui.show_image"]
    payload: dict[str, Any]


class AgentOutput(BaseModel):
    type: Literal["speech", "action"]
    speech: str | None = None
    action: UiAction | None = None

    @model_validator(mode="after")
    def validate_content(self) -> "AgentOutput":
        if self.type == "speech" and (not self.speech or self.action is not None):
            raise ValueError("speech output requires only speech")
        if self.type == "action" and (self.action is None or self.speech is not None):
            raise ValueError("action output requires only an action")
        return self


class StudentMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ActionResultRequest(BaseModel):
    result: dict[str, Any]


class PendingToolCall(BaseModel):
    call_id: str
    provider_call_id: str
    name: Literal["show_choices", "show_image"]
    arguments: dict[str, Any]
