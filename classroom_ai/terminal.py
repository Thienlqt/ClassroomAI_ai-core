import json

from classroom_ai.agent import AgentStateError, ClassroomAgent
from classroom_ai.schemas import UiAction
from classroom_ai.tools.registry import ToolError


def handle_action(action: UiAction) -> dict:
    print("\n[CLASSROOM UI EVENT]")
    print(action.model_dump_json(indent=2))

    if action.type == "ui.show_image":
        print(f"[Mock UI opens: {action.payload['image_url']}]")
        return {"success": True}

    choices = action.payload["choices"]
    print(f"\n{action.payload['question']}")
    for index, choice in enumerate(choices, start=1):
        print(f"{index}. {choice}")

    while True:
        try:
            selected_index = int(input("\nChoose: ")) - 1
        except ValueError:
            selected_index = -1
        if 0 <= selected_index < len(choices):
            return {"selected": choices[selected_index]}
        print(f"Please enter a number from 1 to {len(choices)}.")


def main() -> None:
    agent = ClassroomAgent()
    messages = agent.new_conversation()

    print("\nAI English Classroom")
    print("Type 'quit' to stop.\n")

    while True:
        student = input("Student: ").strip()
        if student.casefold() == "quit":
            break
        if not student:
            continue

        try:
            output, pending = agent.submit_message(messages, student)
        except (AgentStateError, ToolError, ValueError) as error:
            print("\n[Agent error]", error)
            continue
        if output.type == "speech":
            print("\nTeacher:", output.speech)
            continue

        result = handle_action(output.action)
        print("\n[App result]", json.dumps(result))
        feedback = agent.submit_action_result(messages, pending, result)
        print("\nTeacher:", feedback.speech)
