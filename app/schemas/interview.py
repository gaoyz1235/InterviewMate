from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["项目深挖", "技术基础", "岗位匹配", "行为动机"]
InterviewAction = Literal["continue", "follow_up", "finish"]


class ResumeProject(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    evidence: str = ""


class ResumeAnalysis(BaseModel):
    projects: list[ResumeProject] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    summary: str = ""


class InterviewQuestion(BaseModel):
    question_id: str
    question_type: QuestionType
    question: str
    related_resume: str = ""
    follow_up_depth: int = 0


class InterviewPlan(BaseModel):
    questions: list[InterviewQuestion]
    total_questions: int
    duration_minutes: int = Field(default=10, ge=3, le=60)
    current_index: int = 0


class InterviewMessage(BaseModel):
    role: Literal["assistant", "user"]
    content: str
    question_id: str | None = None
    question_type: QuestionType | None = None
    elapsed_seconds: int | None = None


class InterviewContext(BaseModel):
    session_id: str
    resume_text: str
    target_company: str = ""
    target_role: str = ""
    duration_minutes: int = Field(default=10, ge=3, le=60)
    analysis: ResumeAnalysis
    plan: InterviewPlan
    history: list[InterviewMessage] = Field(default_factory=list)
    started_at: float
    finished: bool = False


class StartInterviewResponse(BaseModel):
    session_id: str
    analysis: ResumeAnalysis
    plan: InterviewPlan
    question: InterviewQuestion
    progress: str


class AnswerRequest(BaseModel):
    question_id: str
    answer: str = Field(min_length=1)
    elapsed_seconds: int = Field(default=0, ge=0)


class AnswerResponse(BaseModel):
    action: InterviewAction
    question: InterviewQuestion | None = None
    progress: str
    message: str = ""


class ScoreItem(BaseModel):
    name: str
    score: int = Field(ge=0, le=25)
    comment: str


class InterviewSummary(BaseModel):
    session_id: str
    total_score: int = Field(ge=0, le=100)
    scores: list[ScoreItem]
    exposed_problems: list[str]
    resume_suggestions: list[str]
    practice_suggestions: list[str]
    transcript: list[InterviewMessage]
