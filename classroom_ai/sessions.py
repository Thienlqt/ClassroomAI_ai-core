from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from classroom_ai.agent import ClassroomAgent
from classroom_ai.schemas import PendingToolCall


@dataclass
class ClassroomSession:
    messages: list[Any]
    pending: PendingToolCall | None = None
    lock: RLock = field(default_factory=RLock)


class SessionStore:
    """Small in-memory store for the prototype; replaceable behind the API later."""

    def __init__(self, agent: ClassroomAgent):
        self.agent = agent
        self._sessions: dict[str, ClassroomSession] = {}
        self._lock = RLock()

    def get_or_create(self, session_id: str) -> ClassroomSession:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ClassroomSession(
                    messages=self.agent.new_conversation()
                )
            return self._sessions[session_id]

    def get(self, session_id: str) -> ClassroomSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None
