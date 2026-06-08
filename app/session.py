import uuid
from anthropic.types import MessageParam


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[MessageParam]] = {}

    def new_session(self) ->str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = []
        return session_id

    def append(self, session_id: str, message: MessageParam) -> None:
        self._sessions.setdefault(session_id, []).append(message)

    def get(self, session_id: str) -> list[MessageParam]:
        return self._sessions.get(session_id, [])

_store = SessionStore()

def get_session_store() -> SessionStore:
    return _store