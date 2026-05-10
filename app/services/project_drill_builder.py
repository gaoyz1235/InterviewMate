import logging

from app.schemas.interview import InterviewPlan, InterviewQuestion
from app.services.llm_client import LLMClient
from app.services.prompt_builder import build_project_drill_plan_prompt

logger = logging.getLogger(__name__)


def build_project_drill_plan(
    project_text: str,
    question_focus: str,
    target_company: str,
    target_role: str,
    round_count: int,
) -> InterviewPlan:
    safe_round_count = min(max(round_count, 1), 3)
    questions = _build_questions_with_llm(
        project_text=project_text,
        question_focus=question_focus,
        target_company=target_company,
        target_role=target_role,
        round_count=safe_round_count,
    )
    if len(questions) < safe_round_count:
        logger.warning(
            "project_drill.llm_incomplete expected=%s actual=%s fallback_count=%s",
            safe_round_count,
            len(questions),
            safe_round_count - len(questions),
        )
        questions.extend(
            _build_fallback_questions(
                project_text=project_text,
                question_focus=question_focus,
                existing_count=len(questions),
                total_count=safe_round_count,
            )
        )

    return InterviewPlan(
        questions=questions[:safe_round_count],
        total_questions=safe_round_count,
        duration_minutes=safe_round_count * 5,
    )


def _build_questions_with_llm(
    project_text: str,
    question_focus: str,
    target_company: str,
    target_role: str,
    round_count: int,
) -> list[InterviewQuestion]:
    client = LLMClient()
    if not client.configured:
        logger.info("project_drill.llm.skip reason=not_configured")
        return []

    data = client.chat_json(
        "你是一名擅长项目深挖的互联网大厂技术面试官，只输出 JSON。",
        build_project_drill_plan_prompt(
            project_text=project_text,
            question_focus=question_focus,
            target_company=target_company,
            target_role=target_role,
            round_count=round_count,
        ),
        timeout_seconds=120,
    )
    items = data.get("questions", [])
    if not isinstance(items, list):
        logger.warning("project_drill.llm.invalid reason=questions_not_list")
        return []

    questions: list[InterviewQuestion] = []
    for index, item in enumerate(items[:round_count], start=1):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            logger.warning("project_drill.llm.missing_question index=%s", index)
            continue
        questions.append(
            InterviewQuestion(
                question_id=f"p{index}",
                question_type="项目强化",
                question=question,
                related_resume=str(item.get("related_resume") or project_text[:500]).strip(),
            )
        )

    logger.info("project_drill.llm.done generated=%s expected=%s focus=%s", len(questions), round_count, question_focus)
    return questions


def _build_fallback_questions(
    project_text: str,
    question_focus: str,
    existing_count: int,
    total_count: int,
) -> list[InterviewQuestion]:
    fallback_templates = [
        f"请先用 2 分钟介绍这个项目的背景、你的个人职责，以及它和「{question_focus}」最相关的部分。",
        "这个项目里最关键的技术难点是什么？你当时有哪些方案选择，最终为什么选现在这个方案？",
        "如果这个项目的数据量、用户量或请求量扩大 10 倍，你会优先改造哪一部分？为什么？",
        "这个项目当前最大的边界条件或潜在风险是什么？如果面试官继续追问，你会如何证明自己真的做过？",
        "请把这个项目改写成一段更适合简历的表述，重点体现个人贡献、技术方案和可验证结果。",
    ]
    needed = total_count - existing_count
    questions = []
    for offset, question in enumerate(fallback_templates[:needed], start=1):
        index = existing_count + offset
        questions.append(
            InterviewQuestion(
                question_id=f"p{index}",
                question_type="项目强化",
                question=question,
                related_resume=project_text[:500],
            )
        )
    return questions
