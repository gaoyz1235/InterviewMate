import json
import logging
import random

from app.schemas.interview import InterviewPlan, InterviewQuestion, QuestionType, ResumeAnalysis
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

QUESTION_TYPES: list[QuestionType] = ["项目深挖", "技术基础", "岗位匹配", "行为动机"]


def build_interview_plan(
    analysis: ResumeAnalysis,
    target_company: str,
    target_role: str,
    duration_minutes: int,
) -> InterviewPlan:
    question_count = _question_count_for_duration(duration_minutes)
    question_types = _choose_question_types(question_count)
    questions = _build_questions_with_llm(
        analysis=analysis,
        target_company=target_company,
        target_role=target_role,
        duration_minutes=duration_minutes,
        question_types=question_types,
    )

    if len(questions) < question_count:
        logger.warning(
            "plan_builder.llm_incomplete expected=%s actual=%s fallback_count=%s",
            question_count,
            len(questions),
            question_count - len(questions),
        )
        questions.extend(_build_fallback_questions(analysis, question_types[len(questions) :], len(questions)))

    return InterviewPlan(
        questions=questions,
        total_questions=len(questions),
        duration_minutes=duration_minutes,
    )


def _choose_question_types(question_count: int) -> list[QuestionType]:
    selected: list[QuestionType] = []
    while len(selected) < question_count:
        pool = QUESTION_TYPES.copy()
        random.shuffle(pool)
        selected.extend(pool)
    result = selected[:question_count]
    logger.info("plan_builder.question_types selected=%s", result)
    return result


def _build_questions_with_llm(
    analysis: ResumeAnalysis,
    target_company: str,
    target_role: str,
    duration_minutes: int,
    question_types: list[QuestionType],
) -> list[InterviewQuestion]:
    client = LLMClient()
    if not client.configured:
        logger.info("plan_builder.llm.skip reason=not_configured")
        return []

    data = client.chat_json(
        "你是一名互联网大厂技术岗一面面试官，只输出 JSON，不输出 Markdown。",
        _build_plan_prompt(
            analysis=analysis,
            target_company=target_company,
            target_role=target_role,
            duration_minutes=duration_minutes,
            question_types=question_types,
        ),
        timeout_seconds=120,
    )
    items = data.get("questions", [])
    if not isinstance(items, list):
        logger.warning("plan_builder.llm.invalid reason=questions_not_list")
        return []

    questions: list[InterviewQuestion] = []
    for index, question_type in enumerate(question_types, start=1):
        item = items[index - 1] if index - 1 < len(items) and isinstance(items[index - 1], dict) else {}
        question = str(item.get("question") or "").strip()
        if not question:
            logger.warning("plan_builder.llm.missing_question index=%s question_type=%s", index, question_type)
            continue
        questions.append(
            InterviewQuestion(
                question_id=f"q{index}",
                question_type=question_type,
                question=question,
                related_resume=str(item.get("related_resume") or "").strip(),
            )
        )

    logger.info("plan_builder.llm.done generated=%s expected=%s", len(questions), len(question_types))
    return questions


def _build_plan_prompt(
    analysis: ResumeAnalysis,
    target_company: str,
    target_role: str,
    duration_minutes: int,
    question_types: list[QuestionType],
) -> str:
    analysis_json = json.dumps(analysis.model_dump(), ensure_ascii=False)
    return f"""
请根据候选人的简历分析结果，生成一轮模拟面试的问题列表。

要求：
1. 必须严格按照给定题型顺序生成问题：{question_types}
2. 每个问题只问一个点，短而具体，像真实技术一面。
3. 优先围绕简历中的项目、技能和风险点提问，不要编造简历没有的信息。
4. 如果题型是“项目深挖”，要追问候选人的职责、技术方案、难点、取舍、结果或边界。
5. 如果题型是“技术基础”，要结合简历技能和目标岗位问原理或落地问题。
6. 如果题型是“岗位匹配”，要问候选人与目标公司/岗位的匹配证据。
7. 如果题型是“行为动机”，要问项目协作、困难解决、动机或复盘。
8. 只输出 JSON，格式如下：
{{
  "questions": [
    {{
      "question_type": "项目深挖",
      "question": "问题文本",
      "related_resume": "该问题关联的简历证据，若没有则为空字符串"
    }}
  ]
}}

目标公司：{target_company or "未指定"}
目标岗位：{target_role or "技术实习生"}
面试时长：{duration_minutes} 分钟
简历分析结果：{analysis_json}
""".strip()


def _build_fallback_questions(
    analysis: ResumeAnalysis,
    question_types: list[QuestionType],
    existing_count: int,
) -> list[InterviewQuestion]:
    project = analysis.projects[0] if analysis.projects else None
    project_text = project.evidence if project else analysis.summary
    skills = "、".join(analysis.skills[:5]) or "简历中的核心技能"
    fallback_questions = {
        "项目深挖": f"请围绕简历中最重要的项目，说明你的个人职责、关键技术方案和最终结果。关联信息：{project_text[:80]}",
        "技术基础": f"请结合 {skills} 中你最熟悉的一项，说明它的核心原理以及你在项目中的使用方式。",
        "岗位匹配": "请说明你的项目经历和目标岗位最匹配的地方，并给出简历中的具体证据。",
        "行为动机": "请讲一次你在项目中遇到困难并解决的经历，重点说明你的判断、行动和复盘。",
    }
    return [
        InterviewQuestion(
            question_id=f"q{existing_count + index}",
            question_type=question_type,
            question=fallback_questions[question_type],
            related_resume=project_text,
        )
        for index, question_type in enumerate(question_types, start=1)
    ]


def _question_count_for_duration(duration_minutes: int) -> int:
    if duration_minutes <= 8:
        return 2
    if duration_minutes <= 15:
        return 3
    if duration_minutes <= 25:
        return 4
    return 5
