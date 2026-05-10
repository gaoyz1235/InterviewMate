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


def build_resume_analysis_prompt(resume_text: str) -> str:
    return f"""
请作为互联网大厂技术面试官，解析以下脱敏简历，提取用于模拟面试的结构化信息。

要求：
1. 不要编造简历中没有的信息。
2. 项目经历要尽量保留能被追问的证据，例如职责、技术栈、指标、难点、成果。
3. 技能关键词要从简历中提取，包含语言、框架、数据库、中间件、算法、工程能力等。
4. 风险点要从面试官视角指出，例如职责不清、缺少量化指标、技术深度不足、项目边界不清、岗位匹配证据弱。
5. summary 用 1-2 句话总结候选人可深挖方向。
6. 只输出 JSON，不要输出 Markdown。

输出格式：
{{
  "projects": [
    {{
      "name": "项目名称",
      "description": "项目简介和候选人职责",
      "technologies": ["技术1", "技术2"],
      "evidence": "简历中支持该项目提取的原文或摘要"
    }}
  ],
  "skills": ["技能1", "技能2"],
  "risks": ["风险点1", "风险点2"],
  "summary": "总结"
}}

简历文本：
{resume_text[:8000]}
""".strip()


def build_project_drill_plan_prompt(
    project_text: str,
    question_focus: str,
    target_company: str,
    target_role: str,
    round_count: int,
) -> str:
    return f"""
请作为互联网大厂技术面试官，围绕候选人提供的单个项目经历生成项目强化训练问题。

要求：
1. 总共生成 {round_count} 个主问题，问题之间要有递进关系。
2. 提问方向：{question_focus or "综合项目深挖"}。
3. 每个问题只问一个重点，短而具体，适合技术一面。
4. 必须紧扣项目经历，不要编造项目中没有的信息。
5. 问题要覆盖职责、技术方案、难点、取舍、边界、指标、复盘中的若干方面。
6. 只输出 JSON，不要输出 Markdown。

输出格式：
{{
  "questions": [
    {{
      "question": "问题文本",
      "related_resume": "该问题关联的项目证据，若没有则为空字符串"
    }}
  ]
}}

目标公司：{target_company or "未指定"}
目标岗位：{target_role or "技术实习生"}
项目经历：
{project_text[:8000]}
""".strip()


def build_project_drill_summary_prompt(project_text: str, question_focus: str, transcript: str) -> str:
    return f"""
请根据项目强化训练记录，输出针对单个重点项目的复盘 JSON。

评分要求：
- 项目表达：是否讲清背景、个人职责、关键方案和结果。
- 技术深度：是否讲清原理、取舍、边界、替代方案和风险。
- 抗追问能力：面对连续追问是否能给出具体细节。
- 简历呈现：这个项目写在简历上是否有说服力。

只输出 JSON：
{{
  "scores": [
    {{"name": "项目表达", "score": 0-25, "comment": "一句话"}},
    {{"name": "技术深度", "score": 0-25, "comment": "一句话"}},
    {{"name": "抗追问能力", "score": 0-25, "comment": "一句话"}},
    {{"name": "简历呈现", "score": 0-25, "comment": "一句话"}}
  ],
  "exposed_problems": ["问题1", "问题2"],
  "resume_suggestions": ["如何改写这个项目经历"],
  "practice_suggestions": ["下一轮针对该项目练什么"]
}}

提问方向：{question_focus or "综合项目深挖"}
项目经历：
{project_text[:4000]}

训练记录：
{transcript}
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
