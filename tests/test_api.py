import base64
import re

from fastapi.testclient import TestClient

from classroom_ai.agent import ClassroomAgent
from classroom_ai.api import create_app
from classroom_ai.content import load_image_catalog
from classroom_ai.vision.schemas import BoundingBox, RecognizedFace
from tests.helpers import FakeModel, model_message, tool_call


class FakeSpeech:
    def synthesize(self, text, language="en-US"):
        return b"RIFF-fake-" + language.encode() + b"-" + text.encode()


class FakeTranscriber:
    def transcribe(self, audio):
        assert audio == b"fake-browser-audio"
        return "Can an eagle fly?"


class FakeFaceRecognition:
    def __init__(self):
        self.enrollments = []

    def recognize(self, image_bytes):
        assert image_bytes == b"fake-image"
        return [
            RecognizedFace(
                bounds=BoundingBox(x_min=0.1, y_min=0.2, x_max=0.3, y_max=0.8),
                detection_score=0.98,
                subject_id="student-1",
                display_name="Student One",
                similarity=0.82,
            )
        ]

    def enroll(
        self,
        image_bytes,
        *,
        subject_id,
        display_name,
        consent_reference,
    ):
        self.enrollments.append(
            (image_bytes, subject_id, display_name, consent_reference)
        )
        return 42


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
            "segments": [
                {"language": "en-US", "text": "Correct! The eagle can fly."}
            ],
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
        script_path = re.search(r'src="([^"]+\.js)"', page.text).group(1)
        style_path = re.search(r'href="([^"]+\.css)"', page.text).group(1)
        script = client.get(script_path)
        styles = client.get(style_path)

    assert page.status_code == 200
    assert "ClassroomAI" in page.text
    assert 'id="app"' in page.text
    assert script.status_code == 200
    assert "/v1/sessions/" in script.text
    assert "/v1/faces/enroll" in script.text
    assert "ui.show_choices" in script.text
    assert "ui.show_image" in script.text
    assert styles.status_code == 200
    assert ".classroom" in styles.text


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


def test_app_exposes_local_speech_as_wav():
    agent = ClassroomAgent(model=FakeModel([]), image_catalog=load_image_catalog())

    with TestClient(create_app(agent, speech=FakeSpeech())) as client:
        response = client.post(
            "/v1/speech", json={"text": "Xin chào", "language": "vi-VN"}
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == "RIFF-fake-vi-VN-Xin chào".encode()


def test_app_exposes_local_audio_transcription():
    agent = ClassroomAgent(model=FakeModel([]), image_catalog=load_image_catalog())

    with TestClient(create_app(agent, transcriber=FakeTranscriber())) as client:
        response = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("student.webm", b"fake-browser-audio", "audio/webm")},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "Can an eagle fly?"}


def test_app_exposes_server_side_cosine_face_recognition():
    agent = ClassroomAgent(model=FakeModel([]), image_catalog=load_image_catalog())
    encoded = base64.b64encode(b"fake-image").decode()

    with TestClient(
        create_app(agent, face_recognition=FakeFaceRecognition())
    ) as client:
        response = client.post(
            "/v1/faces/recognize", json={"image_base64": encoded}
        )

    assert response.status_code == 200
    assert response.json()[0]["bounds"]["x_min"] == 0.1
    assert response.json()[0]["subject_id"] == "student-1"
    assert response.json()[0]["similarity"] == 0.82


def test_app_requires_consent_and_enrolls_a_face():
    agent = ClassroomAgent(model=FakeModel([]), image_catalog=load_image_catalog())
    face_service = FakeFaceRecognition()
    encoded = base64.b64encode(b"fake-image").decode()

    with TestClient(create_app(agent, face_recognition=face_service)) as client:
        rejected = client.post(
            "/v1/faces/enroll",
            json={
                "image_base64": encoded,
                "subject_id": "student-self",
                "display_name": "Student",
                "consent_confirmed": False,
                "consent_reference": "browser-confirmation:test",
            },
        )
        enrolled = client.post(
            "/v1/faces/enroll",
            json={
                "image_base64": encoded,
                "subject_id": "student-self",
                "display_name": "Student",
                "consent_confirmed": True,
                "consent_reference": "browser-confirmation:test",
            },
        )

    assert rejected.status_code == 422
    assert enrolled.status_code == 200
    assert enrolled.json() == {
        "embedding_id": 42,
        "subject_id": "student-self",
        "display_name": "Student",
    }
    assert face_service.enrollments == [
        (b"fake-image", "student-self", "Student", "browser-confirmation:test")
    ]
