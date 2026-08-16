import base64
import binascii

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from classroom_ai.agent import AgentStateError, ClassroomAgent
from classroom_ai.audio.piper import PiperSpeech, PiperUnavailableError
from classroom_ai.audio.whisper_cpp import (
    TranscriptionError,
    TranscriptionUnavailableError,
    WhisperCppTranscriber,
)
from classroom_ai.config import settings
from classroom_ai.schemas import (
    ActionResultRequest,
    AgentOutput,
    ImageFrameRequest,
    SpeechRequest,
    StudentMessageRequest,
    TranscriptionResult,
)
from classroom_ai.sessions import SessionStore
from classroom_ai.tools.registry import ToolError
from classroom_ai.vision.base import (
    FaceRecognitionService,
    FaceRecognitionUnavailableError,
)
from classroom_ai.vision.face_recognition import OpenCVFaceRecognition
from classroom_ai.vision.schemas import (
    FaceEnrollmentRequest,
    FaceEnrollmentResult,
    RecognizedFace,
)


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 15 * 1024 * 1024


def _decode_image(value: str) -> bytes:
    encoded = value.strip()
    if encoded.startswith("data:"):
        try:
            metadata, encoded = encoded.split(",", 1)
        except ValueError as error:
            raise ValueError("Invalid image data URL") from error
        if ";base64" not in metadata:
            raise ValueError("Image data URL must use base64 encoding")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("image_base64 is not valid base64") from error
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Decoded image cannot exceed 10 MiB")
    return image_bytes


def create_app(
    agent: ClassroomAgent | None = None,
    store: SessionStore | None = None,
    speech: PiperSpeech | None = None,
    transcriber: WhisperCppTranscriber | None = None,
    face_recognition: FaceRecognitionService | None = None,
) -> FastAPI:
    classroom_agent = agent or ClassroomAgent()
    session_store = store or SessionStore(classroom_agent)
    speech_service = speech or PiperSpeech()
    transcription_service = transcriber or WhisperCppTranscriber()
    face_service = face_recognition or OpenCVFaceRecognition()

    app = FastAPI(
        title="Spatial AI Classroom Core",
        version="0.1.0",
        description="Local Gemma teaching agent and semantic classroom UI protocol.",
    )
    app.state.agent = classroom_agent
    app.state.sessions = session_store
    app.state.speech = speech_service
    app.state.transcriber = transcription_service
    app.state.face_recognition = face_service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount(
        "/assets/images",
        StaticFiles(directory=settings.images_dir),
        name="classroom-images",
    )
    app.mount(
        "/static",
        StaticFiles(directory=settings.frontend_dir),
        name="classroom-app-static",
    )
    app.mount(
        "/assets/avatar",
        StaticFiles(directory=settings.avatar_dir, check_dir=False),
        name="teacher-avatar",
    )

    @app.get("/", include_in_schema=False)
    def classroom_app() -> FileResponse:
        return FileResponse(settings.frontend_dir / "index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "model": settings.model,
            "provider": settings.model_provider,
        }

    @app.post(
        "/v1/sessions/{session_id}/messages",
        response_model=AgentOutput,
    )
    def send_message(session_id: str, request: StudentMessageRequest) -> AgentOutput:
        session = session_store.get_or_create(session_id)
        with session.lock:
            if session.pending is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Complete the pending classroom action first.",
                )
            try:
                output, pending = classroom_agent.submit_message(
                    session.messages,
                    request.message,
                )
            except (AgentStateError, ToolError, ValueError) as error:
                raise HTTPException(status_code=502, detail=str(error)) from error

            session.pending = pending
            return output

    @app.post(
        "/v1/sessions/{session_id}/actions/{call_id}/result",
        response_model=AgentOutput,
    )
    def send_action_result(
        session_id: str,
        call_id: str,
        request: ActionResultRequest,
    ) -> AgentOutput:
        session = session_store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")

        with session.lock:
            if session.pending is None:
                raise HTTPException(status_code=409, detail="No classroom action is pending.")
            if session.pending.call_id != call_id:
                raise HTTPException(status_code=409, detail="Action call_id does not match.")

            try:
                output = classroom_agent.submit_action_result(
                    session.messages,
                    session.pending,
                    request.result,
                )
            except ToolError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            except (AgentStateError, ValueError) as error:
                raise HTTPException(status_code=502, detail=str(error)) from error

            session.pending = None
            return output

    @app.delete("/v1/sessions/{session_id}", status_code=204)
    def delete_session(session_id: str) -> None:
        session_store.delete(session_id)

    @app.post("/v1/speech", response_class=Response)
    def synthesize_speech(request: SpeechRequest) -> Response:
        try:
            audio = speech_service.synthesize(request.text, request.language)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PiperUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return Response(
            content=audio,
            media_type="audio/wav",
            headers={"Content-Disposition": 'inline; filename="speech.wav"'},
        )

    @app.post("/v1/audio/transcriptions", response_model=TranscriptionResult)
    def transcribe_audio(file: UploadFile = File(...)) -> TranscriptionResult:
        audio = file.file.read(MAX_AUDIO_BYTES + 1)
        file.file.close()
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Audio cannot exceed 15 MiB.")
        try:
            text = transcription_service.transcribe(audio)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except TranscriptionUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except TranscriptionError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        return TranscriptionResult(text=text)

    @app.post("/v1/faces/recognize", response_model=list[RecognizedFace])
    def recognize_faces(request: ImageFrameRequest) -> list[RecognizedFace]:
        try:
            return face_service.recognize(_decode_image(request.image_base64))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except FaceRecognitionUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/v1/faces/enroll", response_model=FaceEnrollmentResult)
    def enroll_face(request: FaceEnrollmentRequest) -> FaceEnrollmentResult:
        try:
            embedding_id = face_service.enroll(
                _decode_image(request.image_base64),
                subject_id=request.subject_id,
                display_name=request.display_name,
                consent_reference=request.consent_reference,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except FaceRecognitionUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return FaceEnrollmentResult(
            embedding_id=embedding_id,
            subject_id=request.subject_id,
            display_name=request.display_name,
        )

    return app


app = create_app()
