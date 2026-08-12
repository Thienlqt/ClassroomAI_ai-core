from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from classroom_ai.agent import AgentStateError, ClassroomAgent
from classroom_ai.config import settings
from classroom_ai.schemas import ActionResultRequest, AgentOutput, StudentMessageRequest
from classroom_ai.sessions import SessionStore
from classroom_ai.tools.registry import ToolError


def create_app(
    agent: ClassroomAgent | None = None,
    store: SessionStore | None = None,
) -> FastAPI:
    classroom_agent = agent or ClassroomAgent()
    session_store = store or SessionStore(classroom_agent)

    app = FastAPI(
        title="Spatial AI Classroom Core",
        version="0.1.0",
        description="Local Gemma teaching agent and semantic classroom UI protocol.",
    )
    app.state.agent = classroom_agent
    app.state.sessions = session_store
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

    return app


app = create_app()
