import json
import os
from typing import Any, Protocol

from classroom_ai.config import Settings, settings


class ModelGateway(Protocol):
    def chat(self, messages: list[Any], tools: list[dict] | None = None) -> dict: ...


def _as_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        return message
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    raise TypeError(f"Unsupported message type: {type(message).__name__}")


def _tool_call_dict(call: Any) -> dict[str, Any]:
    return _as_dict(call)


def _ollama_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Convert provider-neutral history to Ollama's message format."""
    converted = []
    for raw_message in messages:
        message = _as_dict(raw_message)
        role = message["role"]

        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_name": message["tool_name"],
                    "content": message["content"],
                }
            )
            continue

        item: dict[str, Any] = {"role": role, "content": message.get("content", "")}
        if role == "assistant" and message.get("tool_calls"):
            item["tool_calls"] = []
            for raw_call in message["tool_calls"]:
                call = _tool_call_dict(raw_call)
                function = _as_dict(call["function"])
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                item["tool_calls"].append(
                    {
                        "function": {
                            "name": function["name"],
                            "arguments": arguments,
                        }
                    }
                )
        converted.append(item)
    return converted


def _openai_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Convert provider-neutral history to OpenAI-compatible chat messages."""
    converted = []
    for raw_message in messages:
        message = _as_dict(raw_message)
        role = message["role"]

        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": message["tool_call_id"],
                    "content": message["content"],
                }
            )
            continue

        item: dict[str, Any] = {"role": role, "content": message.get("content", "")}
        if role == "assistant" and message.get("tool_calls"):
            item["tool_calls"] = []
            for raw_call in message["tool_calls"]:
                call = _tool_call_dict(raw_call)
                function = _as_dict(call["function"])
                arguments = function.get("arguments", {})
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments)
                item["tool_calls"].append(
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": function["name"],
                            "arguments": arguments,
                        },
                    }
                )
        converted.append(item)
    return converted


class OllamaGateway:
    def __init__(self, model: str = settings.model, host: str = settings.ollama_host):
        # Ollama uses httpx internally. Ensure local inference bypasses shell proxies.
        for key in list(os.environ):
            if "proxy" in key.lower():
                os.environ.pop(key, None)
        os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
        os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
        os.environ.setdefault("OLLAMA_NO_CLOUD", "1")

        from ollama import Client

        self.model = model
        self.client = Client(host=host)

    def chat(self, messages: list[Any], tools: list[dict] | None = None) -> dict:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": _ollama_messages(messages),
        }
        if tools is not None:
            request["tools"] = tools
        response = self.client.chat(**request).message
        return response.model_dump(exclude_none=True)


class OpenAICompatibleGateway:
    """Adapter for llama.cpp and other local OpenAI-compatible servers."""

    def __init__(
        self,
        model: str = settings.model,
        base_url: str = settings.openai_base_url,
        api_key: str = settings.openai_api_key,
    ):
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self, messages: list[Any], tools: list[dict] | None = None) -> dict:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": _openai_messages(messages),
        }
        if tools is not None:
            request["tools"] = tools
            request["parallel_tool_calls"] = False
        response = self.client.chat.completions.create(**request)
        return response.choices[0].message.model_dump(exclude_none=True)


def create_model_gateway(config: Settings = settings) -> ModelGateway:
    provider = config.model_provider.strip().casefold()
    if provider == "ollama":
        return OllamaGateway(model=config.model, host=config.ollama_host)
    if provider in {"llama_cpp", "openai_compatible"}:
        return OpenAICompatibleGateway(
            model=config.model,
            base_url=config.openai_base_url,
            api_key=config.openai_api_key,
        )
    raise ValueError(
        "CLASSROOM_MODEL_PROVIDER must be 'ollama', 'llama_cpp', "
        "or 'openai_compatible'"
    )
