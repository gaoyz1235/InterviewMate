import logging
import time
from uuid import uuid4

from app.schemas.interview import (
    AnswerRequest,
    AnswerResponse,
    InterviewContext,
    InterviewMessage,
    InterviewQuestion,
    InterviewSummary,
    ScoreItem,
)
from app.services.llm_client import LLMClient
from app.services.plan_builder import build_interview_plan
from app.services.prompt_builder import build_follow_up_prompt, build_summary_prompt
from app.services.resume_analyzer import analyze_resume
from app.services.session_store import get_session, save_session

MAX_FOLLOW_UP_DEPTH = 2
MAX_SECONDS_PER_ANSWER = 180
logger = logging.getLogger(__name__)


def start_session(
    resume_text: str,
    target_company: str,
    target_role: str,
    duration_minutes: int,
) -> InterviewContext:
    analysis = analyze_resume(resume_text)
    plan = build_interview_plan(
        analysis=analysis,
        target_company=target_company,
        target_role=target_role,
        duration_minutes=duration_minutes,
    )
    context = InterviewContext(
        session_id=uuid4().hex,
        resume_text=resume_text,
        target_company=target_company,
        target_role=target_role,
        duration_minutes=duration_minutes,
        analysis=analysis,
        plan=plan,
        started_at=time.time(),
    )

    first_question = current_question(context)
    if first_question:
        context.history.append(_assistant_message(first_question))
    logger.info(
        "interview.start session_id=%s resume_chars=%s projects=%s skills=%s risks=%s questions=%s target_company=%s target_role=%s duration_minutes=%s",
        context.session_id,
        len(resume_text),
        len(analysis.projects),
        len(analysis.skills),
        len(analysis.risks),
        plan.total_questions,
        target_company or "<empty>",
        target_role or "<empty>",
        duration_minutes,
    )
    return save_session(context)


def handle_answer(session_id: str, request: AnswerRequest) -> AnswerResponse:
    context = _require_session(session_id)
    if context.finished:
        logger.info("interview.answer.ignored session_id=%s reason=already_finished", session_id)
        return AnswerResponse(action="finish", progress=_progress(context), message="本轮面试已结束。")

    logger.info(
        "interview.answer.received session_id=%s question_id=%s answer_chars=%s elapsed_seconds=%s progress=%s",
        session_id,
        request.question_id,
        len(request.answer.strip()),
        request.elapsed_seconds,
        _progress(context),
    )
    context.history.append(
        InterviewMessage(
            role="user",
            content=request.answer.strip(),
            question_id=request.question_id,
            elapsed_seconds=request.elapsed_seconds,
        )
    )

    if _should_finish_by_time(context):
        context.finished = True
        save_session(context)
        logger.info("interview.finish.trigger session_id=%s reason=time_limit progress=%s", session_id, _progress(context))
        return AnswerResponse(action="finish", progress=_progress(context), message="面试时间已到。")

    current = _question_from_request(context, request.question_id)
    follow_up = _decide_follow_up(current, request) if current else None
    if follow_up:
        context.history.append(_assistant_message(follow_up))
        save_session(context)
        logger.info(
            "interview.answer.action session_id=%s action=follow_up next_question_id=%s follow_up_depth=%s question_type=%s",
            session_id,
            follow_up.question_id,
            follow_up.follow_up_depth,
            follow_up.question_type,
        )
        return AnswerResponse(action="follow_up", question=follow_up, progress=_progress(context))

    if _is_last_question(context):
        context.finished = True
        save_session(context)
        logger.info("interview.finish.trigger session_id=%s reason=plan_completed progress=%s", session_id, _progress(context))
        return AnswerResponse(action="finish", progress=_progress(context), message="面试计划已完成。")

    next_question = _move_to_next_question(context)
    context.history.append(_assistant_message(next_question))
    save_session(context)
    logger.info(
        "interview.answer.action session_id=%s action=continue next_question_id=%s question_type=%s progress=%s",
        session_id,
        next_question.question_id,
        next_question.question_type,
        _progress(context),
    )
    return AnswerResponse(action="continue", question=next_question, progress=_progress(context))


def finish_session(session_id: str) -> InterviewSummary:
    context = _require_session(session_id)
    context.finished = True
    summary = _build_summary(context)
    save_session(context)
    logger.info(
        "interview.summary.done session_id=%s total_score=%s transcript_messages=%s",
        session_id,
        summary.total_score,
        len(summary.transcript),
    )
    return summary


def current_question(context: InterviewContext) -> InterviewQuestion | None:
    if not context.plan.questions:
        return None
    return context.plan.questions[context.plan.current_index]


def _question_from_request(context: InterviewContext, question_id: str) -> InterviewQuestion | None:
    base = current_question(context)
    if base is None:
        return None
    follow_up_depth = _parse_follow_up_depth(question_id)
    return InterviewQuestion(
        question_id=question_id,
        question_type=base.question_type,
        question=base.question,
        related_resume=base.related_resume,
        follow_up_depth=follow_up_depth,
    )


def _parse_follow_up_depth(question_id: str) -> int:
    if "_f" not in question_id:
        return 0
    try:
        return int(question_id.rsplit("_f", 1)[1])
    except ValueError:
        return 0


def _move_to_next_question(context: InterviewContext) -> InterviewQuestion:
    context.plan.current_index = min(
        context.plan.current_index + 1,
        context.plan.total_questions - 1,
    )
    question = current_question(context)
    if question is None:
        raise ValueError("面试计划为空。")
    return question


def _decide_follow_up(question: InterviewQuestion, request: AnswerRequest) -> InterviewQuestion | None:
    if question.follow_up_depth >= MAX_FOLLOW_UP_DEPTH:
        logger.info("interview.follow_up.decision need=false reason=max_depth question_id=%s", question.question_id)
        return None

    llm_decision = _llm_follow_up_decision(question, request)
    if llm_decision is not None:
        need_follow_up, follow_up_question, reason = llm_decision
        logger.info(
            "interview.follow_up.decision source=llm need=%s reason=%r question_id=%s",
            need_follow_up,
            reason,
            question.question_id,
        )
        if not need_follow_up:
            return None
        if follow_up_question:
            return _make_follow_up_question(question, follow_up_question, "llm")
        logger.warning("interview.follow_up.llm_invalid reason=empty_follow_up_question question_id=%s", question.question_id)

    if _should_follow_up_by_rule(question, request):
        return _build_rule_follow_up_question(question, request)
    return None


def _should_follow_up_by_rule(question: InterviewQuestion, request: AnswerRequest) -> bool:
    answer = request.answer.strip()
    if request.elapsed_seconds > MAX_SECONDS_PER_ANSWER:
        logger.info("interview.follow_up.decision source=rule need=true reason=overtime question_id=%s elapsed_seconds=%s", question.question_id, request.elapsed_seconds)
        return True
    if len(answer) < 80:
        logger.info("interview.follow_up.decision source=rule need=true reason=short_answer question_id=%s answer_chars=%s", question.question_id, len(answer))
        return True
    weak_signals = ["不知道", "不清楚", "应该", "大概", "可能", "忘了"]
    matched = [signal for signal in weak_signals if signal in answer]
    if matched:
        logger.info("interview.follow_up.decision source=rule need=true reason=weak_signal question_id=%s signals=%s", question.question_id, matched)
        return True
    logger.info("interview.follow_up.decision source=rule need=false reason=answer_ok question_id=%s", question.question_id)
    return False


def _build_rule_follow_up_question(question: InterviewQuestion, request: AnswerRequest) -> InterviewQuestion:
    if request.elapsed_seconds > MAX_SECONDS_PER_ANSWER:
        follow_up_question = "刚才这题超出了 3 分钟。请你用 30 秒重新概括核心结论，并说明最关键的技术取舍。"
    elif len(request.answer.strip()) < 80:
        follow_up_question = "你的回答比较短。请补充一个具体实现细节：你当时遇到的难点是什么，最终怎么解决？"
    else:
        follow_up_question = "请继续深入一点：这个方案的边界条件或潜在风险是什么？"
    return _make_follow_up_question(question, follow_up_question, "rule")


def _make_follow_up_question(question: InterviewQuestion, follow_up_question: str, source: str) -> InterviewQuestion:
    follow_up = InterviewQuestion(
        question_id=f"{question.question_id}_f{question.follow_up_depth + 1}",
        question_type=question.question_type,
        question=follow_up_question,
        related_resume=question.related_resume,
        follow_up_depth=question.follow_up_depth + 1,
    )
    logger.info(
        "interview.follow_up.build source=%s question_id=%s next_question_id=%s question_chars=%s",
        source,
        question.question_id,
        follow_up.question_id,
        len(follow_up.question),
    )
    return follow_up


def _llm_follow_up_decision(question: InterviewQuestion, request: AnswerRequest) -> tuple[bool, str, str] | None:
    client = LLMClient()
    if not client.configured:
        logger.info("interview.llm_follow_up.skip reason=not_configured question_id=%s", question.question_id)
        return None
    data = client.chat_json(
        "你是严格但友好的互联网技术面试官，只输出 JSON。",
        build_follow_up_prompt(question.question, request.answer, request.elapsed_seconds),
    )
    if "need_follow_up" not in data:
        logger.warning("interview.llm_follow_up.invalid reason=missing_need_follow_up question_id=%s", question.question_id)
        return None
    need_follow_up = bool(data.get("need_follow_up"))
    follow_up = str(data.get("follow_up_question") or "").strip()
    reason = str(data.get("reason") or "").strip()
    logger.info(
        "interview.llm_follow_up.done question_id=%s need_follow_up=%s follow_up_chars=%s reason=%r",
        question.question_id,
        need_follow_up,
        len(follow_up),
        reason,
    )
    return need_follow_up, follow_up, reason


def _build_summary(context: InterviewContext) -> InterviewSummary:
    llm_summary = _llm_summary(context)
    if llm_summary:
        logger.info("interview.summary.source session_id=%s source=llm total_score=%s", context.session_id, llm_summary.total_score)
        return llm_summary

    logger.info("interview.summary.source session_id=%s source=rule", context.session_id)
    answers = [item for item in context.history if item.role == "user"]
    avg_length = sum(len(item.content) for item in answers) / max(len(answers), 1)
    overtime_count = sum(1 for item in answers if (item.elapsed_seconds or 0) > MAX_SECONDS_PER_ANSWER)
    depth_score = 22 if avg_length >= 160 else 17 if avg_length >= 80 else 12
    structure_score = 20 if avg_length >= 120 else 15
    follow_up_score = max(10, 22 - overtime_count * 4)
    match_score = 20 if context.analysis.skills else 15

    scores = [
        ScoreItem(name="简历匹配度", score=match_score, comment="回答能围绕目标岗位和简历项目展开。" if match_score >= 20 else "岗位相关技能证据还不够清晰。"),
        ScoreItem(name="技术深度", score=depth_score, comment="技术细节有一定展开。" if depth_score >= 17 else "回答偏概括，需要补充原理、取舍和边界。"),
        ScoreItem(name="表达结构", score=structure_score, comment="基本能说明背景、行动和结果。" if structure_score >= 20 else "建议按背景、行动、结果组织回答。"),
        ScoreItem(name="抗追问能力", score=follow_up_score, comment="追问下仍能继续展开。" if follow_up_score >= 18 else "需要练习短时间内抓重点回答。"),
    ]
    total = sum(item.score for item in scores)
    exposed = _exposed_problems(context, avg_length, overtime_count)
    return InterviewSummary(
        session_id=context.session_id,
        total_score=total,
        scores=scores,
        exposed_problems=exposed,
        resume_suggestions=_resume_suggestions(context, exposed),
        practice_suggestions=_practice_suggestions(exposed),
        transcript=context.history,
    )


def _llm_summary(context: InterviewContext) -> InterviewSummary | None:
    client = LLMClient()
    if not client.configured:
        logger.info("interview.llm_summary.skip session_id=%s reason=not_configured", context.session_id)
        return None
    transcript = "\n".join(f"{item.role}: {item.content}" for item in context.history)
    data = client.chat_json("你是互联网大厂技术面试复盘专家，只输出 JSON。", build_summary_prompt(transcript))
    if not data:
        logger.info("interview.llm_summary.empty session_id=%s", context.session_id)
        return None
    try:
        scores = [ScoreItem(**item) for item in data.get("scores", [])]
        total = sum(item.score for item in scores)
        return InterviewSummary(
            session_id=context.session_id,
            total_score=total,
            scores=scores,
            exposed_problems=list(data.get("exposed_problems", [])),
            resume_suggestions=list(data.get("resume_suggestions", [])),
            practice_suggestions=list(data.get("practice_suggestions", [])),
            transcript=context.history,
        )
    except Exception as exc:
        logger.exception("interview.llm_summary.invalid session_id=%s error=%s", context.session_id, exc.__class__.__name__)
        return None


def _exposed_problems(context: InterviewContext, avg_length: float, overtime_count: int) -> list[str]:
    problems = list(context.analysis.risks[:2])
    if avg_length < 80:
        problems.append("回答缺少具体例子，面试官难以判断真实贡献。")
    if overtime_count:
        problems.append("部分回答超过 3 分钟，需要压缩表达并先给结论。")
    return problems[:4] or ["本轮没有明显致命问题，但仍需补充更具体的项目指标。"]


def _resume_suggestions(context: InterviewContext, exposed: list[str]) -> list[str]:
    suggestions = []
    if any("指标" in item or "量化" in item for item in exposed):
        suggestions.append("把项目结果改成可验证指标，例如性能提升、响应时间、用户量、错误率或通过率。")
    if any("职责" in item for item in exposed):
        suggestions.append("每段项目经历补充个人贡献，避免只写团队成果。")
    if context.analysis.projects:
        suggestions.append(f"围绕「{context.analysis.projects[0].name}」补充技术方案、难点和取舍，方便面试时深挖。")
    suggestions.append("删除空泛形容词，把“熟悉/了解”替换为具体使用场景和产出。")
    return suggestions[:4]


def _practice_suggestions(exposed: list[str]) -> list[str]:
    suggestions = [
        "准备一个 2 分钟项目介绍模板：背景、职责、方案、结果、反思。",
        "针对简历前三个技能点各准备一个原理题和一个项目落地例子。",
    ]
    if any("3 分钟" in item for item in exposed):
        suggestions.append("用计时器练习 30 秒结论版和 2 分钟展开版回答。")
    suggestions.append("每次练习后记录被追问卡住的问题，反向补充简历和知识点。")
    return suggestions[:4]


def _is_last_question(context: InterviewContext) -> bool:
    return context.plan.current_index >= context.plan.total_questions - 1


def _should_finish_by_time(context: InterviewContext) -> bool:
    return time.time() - context.started_at >= context.duration_minutes * 60


def _assistant_message(question: InterviewQuestion) -> InterviewMessage:
    return InterviewMessage(
        role="assistant",
        content=question.question,
        question_id=question.question_id,
        question_type=question.question_type,
    )


def _progress(context: InterviewContext) -> str:
    current = min(context.plan.current_index + 1, context.plan.total_questions)
    return f"{current}/{context.plan.total_questions}"


def _require_session(session_id: str) -> InterviewContext:
    context = get_session(session_id)
    if context is None:
        logger.warning("interview.session.missing session_id=%s", session_id)
        raise ValueError("面试会话不存在或已过期。")
    return context
