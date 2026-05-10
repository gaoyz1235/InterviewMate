from app.schemas.interview import InterviewPlan, InterviewQuestion, ResumeAnalysis


def build_interview_plan(
    analysis: ResumeAnalysis,
    target_company: str,
    target_role: str,
    duration_minutes: int,
) -> InterviewPlan:
    question_count = _question_count_for_duration(duration_minutes)
    questions: list[InterviewQuestion] = []

    project = analysis.projects[0] if analysis.projects else None
    project_name = project.name if project else "你最熟悉的项目"
    related_resume = project.evidence if project else ""
    role = target_role or "目标岗位"
    company = target_company or "目标公司"

    templates = [
        (
            "项目深挖",
            f"请介绍简历中「{project_name}」这个项目：背景是什么，你负责哪一部分，最关键的技术方案是什么？",
            related_resume,
        ),
        (
            "技术基础",
            f"结合{role}的要求，请选择你简历里最重要的一个技术点，说明它的核心原理和你在项目里如何使用。",
            ", ".join(analysis.skills[:8]),
        ),
        (
            "岗位匹配",
            f"如果你面试{company}的{role}，你认为自己的项目经历和岗位最匹配的地方是什么？请给出具体证据。",
            analysis.summary,
        ),
        (
            "项目深挖",
            f"在「{project_name}」里，如果流量、数据量或用户量扩大 10 倍，你会优先改造哪一处？为什么？",
            related_resume,
        ),
        (
            "行为动机",
            f"请讲一次你在项目中遇到困难并解决的经历，重点说明你的判断、行动和结果。",
            related_resume,
        ),
    ]

    for index, (question_type, question, related) in enumerate(templates[:question_count], start=1):
        questions.append(
            InterviewQuestion(
                question_id=f"q{index}",
                question_type=question_type,
                question=question,
                related_resume=related,
            )
        )

    return InterviewPlan(
        questions=questions,
        total_questions=len(questions),
        duration_minutes=duration_minutes,
    )


def _question_count_for_duration(duration_minutes: int) -> int:
    if duration_minutes <= 8:
        return 2
    if duration_minutes <= 15:
        return 3
    if duration_minutes <= 25:
        return 4
    return 5
