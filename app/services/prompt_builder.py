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


def build_follow_up_prompt(question: str, answer: str, elapsed_seconds: int) -> str:
    return f"""
请判断候选人回答是否需要追问，并输出 JSON：
{{
  "need_follow_up": true 或 false,
  "follow_up_question": "如果需要追问，给出一个短问题",
  "reason": "一句话说明"
}}

原问题：{question}
候选人回答耗时：{elapsed_seconds} 秒
候选人回答：{answer}
""".strip()


def build_summary_prompt(transcript: str) -> str:
    return f"""
请根据以下模拟面试记录输出 JSON：
{{
  "scores": [
    {{"name": "简历匹配度", "score": 0-25, "comment": "一句话"}},
    {{"name": "技术深度", "score": 0-25, "comment": "一句话"}},
    {{"name": "表达结构", "score": 0-25, "comment": "一句话"}},
    {{"name": "抗追问能力", "score": 0-25, "comment": "一句话"}}
  ],
  "exposed_problems": ["问题1", "问题2"],
  "resume_suggestions": ["建议1", "建议2"],
  "practice_suggestions": ["建议1", "建议2"]
}}

面试记录：
{transcript}
""".strip()
