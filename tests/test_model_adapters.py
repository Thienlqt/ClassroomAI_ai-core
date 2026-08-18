import json

from classroom_ai.model import _ollama_messages, _openai_messages


def provider_neutral_history():
    return [
        {"role": "user", "content": "Give me a quiz."},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "provider-call-1",
                    "type": "function",
                    "function": {
                        "name": "show_choices",
                        "arguments": {
                            "question": "What can a fish do?",
                            "choices": ["swim", "fly"],
                            "correct_answer": "swim",
                        },
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_name": "show_choices",
            "tool_call_id": "provider-call-1",
            "content": '{"selected": "swim", "correct": true}',
        },
    ]


def test_ollama_adapter_uses_tool_name_and_object_arguments():
    messages = _ollama_messages(provider_neutral_history())

    assert messages[1]["tool_calls"][0]["function"]["arguments"]["question"] == (
        "What can a fish do?"
    )
    assert "id" not in messages[1]["tool_calls"][0]
    assert messages[2]["tool_name"] == "show_choices"
    assert "tool_call_id" not in messages[2]


def test_openai_adapter_uses_call_id_and_json_string_arguments():
    messages = _openai_messages(provider_neutral_history())

    call = messages[1]["tool_calls"][0]
    assert call["id"] == "provider-call-1"
    assert json.loads(call["function"]["arguments"])["correct_answer"] == "swim"
    assert messages[2]["tool_call_id"] == "provider-call-1"
    assert "tool_name" not in messages[2]
