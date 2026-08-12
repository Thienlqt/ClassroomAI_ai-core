from fastapi.testclient import TestClient

from classroom_ai.agent import ClassroomAgent
from classroom_ai.api import create_app
from classroom_ai.content import load_image_catalog
from tests.helpers import FakeModel, model_message, tool_call


def test_app_completes_choice_action_round_trip():
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
            model_message("Correct! The eagle can fly."),
        ]
    )
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())

    with TestClient(create_app(agent)) as client:
        first = client.post(
            "/v1/sessions/class-7a/messages",
            json={"message": "Give me an animal quiz."},
        )
        assert first.status_code == 200
        action = first.json()["action"]
        assert action["type"] == "ui.show_choices"
        assert "correct_answer" not in action["payload"]

        second = client.post(
            f"/v1/sessions/class-7a/actions/{action['call_id']}/result",
            json={"result": {"selected": "Eagle"}},
        )
        assert second.status_code == 200
        assert second.json() == {
            "type": "speech",
            "speech": "Correct! The eagle can fly.",
            "action": None,
        }


def test_app_blocks_new_message_until_pending_action_is_completed():
    model = FakeModel(
        [
            model_message(
                tool_calls=[
                    tool_call("show_image", {"image_id": "lion", "caption": "Lion"})
                ]
            )
        ]
    )
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())

    with TestClient(create_app(agent)) as client:
        first = client.post(
            "/v1/sessions/demo/messages",
            json={"message": "Show me a lion."},
        )
        assert first.status_code == 200
        assert first.json()["action"]["payload"]["image_url"] == (
            "/assets/images/lion.png"
        )

        blocked = client.post(
            "/v1/sessions/demo/messages",
            json={"message": "Another question"},
        )
        assert blocked.status_code == 409


def test_api_serves_catalogued_images():
    model = FakeModel([])
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())

    with TestClient(create_app(agent)) as client:
        response = client.get("/assets/images/lion.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 1000


def test_api_serves_reference_classroom_app():
    model = FakeModel([])
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())

    with TestClient(create_app(agent)) as client:
        page = client.get("/")
        script = client.get("/static/app.js")
        styles = client.get("/static/styles.css")

    assert page.status_code == 200
    assert "Spatial AI Classroom" in page.text
    assert 'id="stageContent"' in page.text
    assert script.status_code == 200
    assert "/v1/sessions/" in script.text
    assert "ui.show_choices" in script.text
    assert "ui.show_image" in script.text
    assert styles.status_code == 200
    assert ".learning-stage" in styles.text


def test_app_completes_image_action_round_trip():
    model = FakeModel(
        [
            model_message(
                tool_calls=[
                    tool_call("show_image", {"image_id": "lion", "caption": "Lion"})
                ]
            ),
            model_message("This is a lion. A lion can roar."),
        ]
    )
    agent = ClassroomAgent(model=model, image_catalog=load_image_catalog())

    with TestClient(create_app(agent)) as client:
        first = client.post(
            "/v1/sessions/image-demo/messages",
            json={"message": "Show me a lion."},
        )
        action = first.json()["action"]
        second = client.post(
            f"/v1/sessions/image-demo/actions/{action['call_id']}/result",
            json={"result": {"success": True}},
        )

    assert first.status_code == 200
    assert action["type"] == "ui.show_image"
    assert action["payload"]["image_url"] == "/assets/images/lion.png"
    assert second.status_code == 200
    assert second.json()["speech"] == "This is a lion. A lion can roar."
