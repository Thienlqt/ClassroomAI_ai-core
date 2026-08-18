from types import SimpleNamespace


def tool_call(name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


def model_message(content: str = "", tool_calls: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


class FakeModel:
    def __init__(self, responses: list[SimpleNamespace]):
        self.responses = iter(responses)
        self.calls: list[dict] = []

    def chat(self, messages: list, tools: list[dict] | None = None):
        self.calls.append({"messages": messages.copy(), "tools": tools})
        return next(self.responses)
