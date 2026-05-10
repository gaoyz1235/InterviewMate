import logging

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.schemas.interview import AnswerRequest, AnswerResponse, InterviewSummary, StartInterviewResponse
from app.services.interview_engine import current_question, finish_session, handle_answer, start_session
from app.services.resume_parser import parse_resume_file

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.post("/api/interviews/start")
async def start_interview(
    target_company: str = Form(""),
    target_role: str = Form(""),
    duration_minutes: int = Form(10),
    resume_text: str = Form(""),
    resume_file: UploadFile | None = File(None),
) -> StartInterviewResponse:
    logger.info(
        "user.start_input has_file=%s resume_text_chars=%s resume_text_preview=%r target_company=%r target_role=%r duration_minutes=%s",
        bool(resume_file and resume_file.filename),
        len(resume_text.strip()),
        _preview(resume_text),
        target_company or "",
        target_role or "",
        duration_minutes,
    )
    parsed_resume = resume_text.strip()
    if resume_file and resume_file.filename:
        parsed_resume = await parse_resume_file(resume_file)
        logger.info(
            "user.resume_file_parsed filename=%r parsed_chars=%s parsed_preview=%r",
            resume_file.filename,
            len(parsed_resume),
            _preview(parsed_resume),
        )

    if not parsed_resume:
        logger.warning("api.start.invalid reason=empty_resume")
        raise HTTPException(status_code=400, detail="请上传 PDF 或粘贴脱敏简历文本。")

    context = start_session(
        resume_text=parsed_resume,
        target_company=target_company,
        target_role=target_role,
        duration_minutes=duration_minutes,
    )
    question = current_question(context)
    if question is None:
        logger.error("api.start.failed reason=no_question session_id=%s", context.session_id)
        raise HTTPException(status_code=500, detail="无法生成面试问题。")

    logger.info(
        "interview.start_response session_id=%s first_question_id=%s first_question=%r progress=1/%s",
        context.session_id,
        question.question_id,
        _preview(question.question),
        context.plan.total_questions,
    )
    return StartInterviewResponse(
        session_id=context.session_id,
        analysis=context.analysis,
        plan=context.plan,
        question=question,
        progress=f"1/{context.plan.total_questions}",
    )


@router.post("/api/interviews/{session_id}/answer", response_model=AnswerResponse)
async def answer_interview(session_id: str, request: AnswerRequest) -> AnswerResponse:
    logger.info(
        "user.answer_input session_id=%s question_id=%s elapsed_seconds=%s answer_chars=%s answer_preview=%r",
        session_id,
        request.question_id,
        request.elapsed_seconds,
        len(request.answer.strip()),
        _preview(request.answer),
    )
    try:
        response = handle_answer(session_id, request)
        logger.info(
            "interview.answer_response session_id=%s action=%s progress=%s next_question=%r",
            session_id,
            response.action,
            response.progress,
            _preview(response.question.question) if response.question else "",
        )
        return response
    except ValueError as exc:
        logger.warning("api.answer.failed session_id=%s error=%s", session_id, str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/interviews/{session_id}/finish", response_model=InterviewSummary)
async def finish_interview(session_id: str) -> InterviewSummary:
    logger.info("user.finish_request session_id=%s", session_id)
    try:
        summary = finish_session(session_id)
        logger.info("interview.finish_response session_id=%s total_score=%s", session_id, summary.total_score)
        return summary
    except ValueError as exc:
        logger.warning("api.finish.failed session_id=%s error=%s", session_id, str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _preview(text: str, limit: int = 300) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
