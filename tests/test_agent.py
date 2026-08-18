from classroom_ai.agent import ClassroomAgent
from classroom_ai.content import load_image_catalog
from tests.helpers import FakeModel, model_message, tool_call


def test_agent_returns_action_then_feedback_without_tools():
    model = FakeModel(
        [
            model_message(
                tool_calls=[
                    tool_call(
                        "show_choices",
                        {
                            "question": "Which animal can fly?",
                            "choices": ["Eagle", "Fish", "Dog"],
                            "correct_answer": "Eagle",
                        },
                    )
                ]
            ),
            model_message("Great! The eagle can fly."),
        ]
    )
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())
    messages = agent.new_conversation()

    action_output, pending = agent.submit_message(messages, "Give me a quiz.")
    feedback = agent.submit_action_result(
        messages,
        pending,
        {"selected": "Eagle"},
    )

    assert action_output.type == "action"
    assert feedback.speech == "Great! The eagle can fly."
    assert model.calls[0]["tools"] is not None
    assert model.calls[1]["tools"] is None
    assert "No image was displayed" in model.calls[1]["messages"][-1]["content"]
    assert messages[-2]["role"] == "tool"
    assert '"correct": true' in messages[-2]["content"]


def test_agent_can_return_speech_without_action():
    model = FakeModel([model_message("Hello! Let's learn about animals.")])
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())

    output, pending = agent.submit_message(agent.new_conversation(), "Hello")

    assert output.type == "speech"
    assert output.speech.startswith("Hello!")
    assert [segment.model_dump() for segment in output.segments] == [
        {"language": "en-US", "text": "Hello! Let's learn about animals."}
    ]
    assert pending is None


def test_agent_returns_clean_bilingual_speech_segments():
    model = FakeModel(
        [
            model_message(
                "[en]A bird can fly.[/en] "
                "[vi]‘Can’ dùng để nói về khả năng.[/vi] "
                "[en]What can a fish do?[/en]"
            )
        ]
    )
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())

    output, pending = agent.submit_message(
        agent.new_conversation(), "Em chưa hiểu từ can."
    )

    assert output.speech == (
        "A bird can fly. ‘Can’ dùng để nói về khả năng. What can a fish do?"
    )
    assert [segment.model_dump() for segment in output.segments] == [
        {"language": "en-US", "text": "A bird can fly."},
        {"language": "vi-VN", "text": "‘Can’ dùng để nói về khả năng."},
        {"language": "en-US", "text": "What can a fish do?"},
    ]
    assert pending is None


def test_agent_gives_invalid_tool_result_back_to_model_for_one_repair():
    model = FakeModel(
        [
            model_message(
                tool_calls=[
                    tool_call(
                        "show_choices",
                        {
                            "question": "Which animal can fly?",
                            "choices": ["Eagle", "Fish"],
                            "correct_answer": "Bird",
                        },
                    )
                ]
            ),
            model_message(
                tool_calls=[
                    tool_call(
                        "show_choices",
                        {
                            "question": "Which animal can fly?",
                            "choices": ["Eagle", "Fish"],
                            "correct_answer": "Eagle",
                        },
                    )
                ]
            ),
        ]
    )
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())
    messages = agent.new_conversation()

    output, pending = agent.submit_message(messages, "Give me a quiz.")

    assert output.type == "action"
    assert pending.arguments["correct_answer"] == "Eagle"
    assert len(model.calls) == 2
    repair_observation = model.calls[1]["messages"][-1]
    assert repair_observation["role"] == "tool"
    assert "Correct the arguments" in repair_observation["content"]


def test_agent_rewrites_feedback_that_claims_an_unavailable_image():
    model = FakeModel(
        [
            model_message(
                tool_calls=[
                    tool_call(
                        "show_choices",
                        {
                            "question": "What can a fish do?",
                            "choices": ["swim", "fly"],
                            "correct_answer": "swim",
                        },
                    )
                ]
            ),
            model_message("Correct! Now look at this picture of a dog."),
            model_message("Correct! A fish can swim. Can you say that sentence?"),
        ]
    )
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())
    messages = agent.new_conversation()
    _, pending = agent.submit_message(messages, "Give me a quiz.")

    feedback = agent.submit_action_result(messages, pending, {"selected": "swim"})

    assert feedback.speech == "Correct! A fish can swim. Can you say that sentence?"
    assert "POLICY CORRECTION" in model.calls[2]["messages"][-1]["content"]
    assert all("look at this picture" not in str(message) for message in messages)
