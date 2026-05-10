def build_interviewer_prompt(
    resume_text: str,
    target_company: str,
    target_role: str,
    duration_minutes: int,
) -> str:
    return f"""
你是一名互联网大厂技术岗一面面试官。

目标公司：{target_company or "未指定"}
目标岗位：{target_role or "技术实习生"}
面试时长：{duration_minutes} 分钟

请基于候选人的脱敏简历进行面试，优先围绕项目经历进行连续追问。
每个问题应该短而具体，避免一次问多个问题。回答后根据质量最多追问 2 次。

简历内容：
{resume_text[:4000]}
""".strip()
