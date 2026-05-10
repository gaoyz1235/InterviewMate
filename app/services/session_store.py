from app.schemas.interview import InterviewContext

_SESSIONS: dict[str, InterviewContext] = {}


def save_session(context: InterviewContext) -> InterviewContext:
    _SESSIONS[context.session_id] = context
    return context


def get_session(session_id: str) -> InterviewContext | None:
    return _SESSIONS.get(session_id)


def delete_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
