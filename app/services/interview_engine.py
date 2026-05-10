from app.services.prompt_builder import build_interviewer_prompt


def build_first_question(
    resume_text: str,
    target_company: str,
    target_role: str,
    duration_minutes: int,
) -> str:
    """Temporary rule-based first question before the LLM adapter is added."""
    _ = build_interviewer_prompt(
        resume_text=resume_text,
        target_company=target_company,
        target_role=target_role,
        duration_minutes=duration_minutes,
    )

    if not resume_text:
        return "请先粘贴或上传一份脱敏简历，我会基于你的项目经历开始模拟面试。"

    role = target_role or "目标岗位"
    company = target_company or "目标公司"
    return (
        f"我们先从项目经历开始。假设你正在面试{company}的{role}，"
        "请你选择简历中最能体现技术深度的一个项目，用 2 分钟介绍背景、你的职责、关键技术方案和最终结果。"
    )
