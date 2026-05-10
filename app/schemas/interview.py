from pydantic import BaseModel, Field


class InterviewMessage(BaseModel):
    role: str
    content: str
    elapsed_seconds: int | None = None


class InterviewContext(BaseModel):
    resume_text: str
    target_company: str = ""
    target_role: str = ""
    duration_minutes: int = Field(default=10, ge=3, le=60)
    history: list[InterviewMessage] = Field(default_factory=list)
