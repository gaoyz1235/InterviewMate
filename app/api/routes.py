from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.interview_engine import build_first_question
from app.services.resume_parser import parse_resume_file

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


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
) -> dict:
    parsed_resume = resume_text.strip()
    if resume_file and resume_file.filename:
        parsed_resume = await parse_resume_file(resume_file)

    question = build_first_question(
        resume_text=parsed_resume,
        target_company=target_company,
        target_role=target_role,
        duration_minutes=duration_minutes,
    )
    return {
        "session_id": "local-demo",
        "resume_text": parsed_resume,
        "question": question,
    }
