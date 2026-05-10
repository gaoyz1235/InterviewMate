import json

from app.schemas.interview import QuestionType, ResumeAnalysis

#早期prompt设计，已经废弃
def build_interviewer_prompt(
    resume_text: str,
    target_company: str,
    target_role: str,
    duration_minutes: int,
) -> str:
    return f"""
你是一名互联网大厂{target_company or ""}的技术岗一面面试官。

目标公司：{target_company or "未指定"}
目标岗位：{target_role or "技术实习生"}
面试时长：{duration_minutes} 分钟

请基于候选人的脱敏简历进行面试，优先围绕项目经历进行连续追问。
每个问题应该短而具体，避免一次问多个问题。回答后根据质量最多追问 2 次。

简历内容：
{resume_text[:4000]}
""".strip()


def build_interview_plan_prompt(
    analysis: ResumeAnalysis,
    target_company: str,
    target_role: str,
    duration_minutes: int,
    question_types: list[QuestionType],
) -> str:
    analysis_json = json.dumps(analysis.model_dump(), ensure_ascii=False)
    return f"""
请以“严格、专业、略有压迫感”的互联网大厂{target_company or ""}的技术一面面试官身份，根据候选人的简历分析结果生成一轮模拟面试问题。

要求：
1. 必须严格按照给定题型顺序生成问题：{question_types}
2. 每个问题只问一个点，短而具体，像真实技术一面，不要客套。
3. 优先围绕简历中的项目、技能和风险点提问，不要编造简历没有的信息。
4. 问题要有区分度：尽量逼候选人讲清个人贡献、技术原理、方案取舍、边界条件、失败风险、指标依据。
5. 可以偶尔出现刁钻但合理的问题，例如“如果不用这个方案怎么办”“指标是否可信”“你怎么证明这是你做的”“规模扩大 10 倍哪里先崩”。
6. 如果题型是“项目深挖”，要追问候选人的职责、技术方案、难点、取舍、结果或边界。
7. 如果题型是“技术基础”，要结合简历技能和目标岗位问原理、复杂度、并发、可靠性或工程落地。
8. 如果题型是“岗位匹配”，要问候选人与目标公司/岗位的匹配证据，避免泛泛自夸。
9. 如果题型是“行为动机”，要问项目协作、冲突解决、失败复盘或自我驱动。
10. 只输出 JSON，格式如下：
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


def build_follow_up_prompt(question: str, answer: str, elapsed_seconds: int) -> str:
    return f"""
请以严格的大厂技术面试官视角，判断候选人回答是否需要追问，并输出 JSON：
{{
  "need_follow_up": true 或 false,
  "follow_up_question": "如果需要追问，给出一个短而有压力的问题",
  "reason": "用面试官思考口吻，一句话说明为什么要追问"
}}

判断标准：
1. 如果回答缺少个人贡献、技术细节、方案取舍、指标依据、边界条件或风险意识，应追问。
2. 如果回答像背稿、泛泛而谈、只讲“做了什么”但不讲“为什么这么做”，应追问。
3. 如果回答足够具体，可以不追问，但要严格判断。
4. 追问要尖锐但公平，不要羞辱候选人；问题应迫使候选人给出证据、细节或推理。

原问题：{question}
候选人回答耗时：{elapsed_seconds} 秒
候选人回答：{answer}
""".strip()


def build_resume_analysis_prompt(resume_text: str) -> str:
    return f"""
请作为严格的互联网大厂技术面试官，解析以下脱敏简历，提取用于模拟面试和压力追问的结构化信息。

要求：
1. 不要编造简历中没有的信息。
2. 项目经历要尽量保留能被追问的证据，例如职责、技术栈、指标、难点、成果、边界条件。
3. 技能关键词要从简历中提取，包含语言、框架、数据库、中间件、算法、工程能力等。
4. 风险点要从面试官视角尖锐指出，例如职责不清、缺少量化指标、技术深度不足、项目边界不清、岗位匹配证据弱、疑似包装、无法证明个人贡献。
5. summary 用 1-2 句话总结候选人最值得深挖和最可能被问崩的方向。
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
请作为严格、专业、略有压迫感的互联网大厂{target_company or ""}的技术面试官，围绕候选人提供的单个项目经历生成项目强化训练问题。

要求：
1. 总共生成 {round_count} 个主问题，问题之间要有递进关系。
2. 提问方向：{question_focus or "综合项目深挖"}。
3. 每个问题只问一个重点，短而具体，适合技术一面，不要客套。
4. 必须紧扣项目经历，不要编造项目中没有的信息。
5. 问题要覆盖职责、技术方案、难点、取舍、边界、指标、复盘中的若干方面。
6. 至少有 1 个问题要有明显压力感或刁钻角度，例如质疑指标、追问替代方案、要求证明个人贡献、要求分析规模扩大后的瓶颈。
7. 问题要能逼候选人说出“为什么这么做”和“如果重来会怎么改”。
8. 只输出 JSON，不要输出 Markdown。

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
请以严格的大厂技术面试官视角，根据项目强化训练记录，输出针对单个重点项目的复盘 JSON。

评分要求：
- 项目表达：是否讲清背景、个人职责、关键方案和结果。
- 技术深度：是否讲清原理、取舍、边界、替代方案和风险。
- 抗追问能力：面对连续追问是否能给出具体细节。
- 简历呈现：这个项目写在简历上是否有说服力。

复盘要求：
- 评价要具体，指出候选人在哪些追问上暴露了问题。
- 不要只说“不错”“需提升”，要指出缺少哪类证据、细节、指标或推理。
- 简历改写要更像真实简历 bullet，突出个人贡献、技术方案、业务/性能结果和可验证指标。

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
  "practice_suggestions": ["下一轮针对该项目练什么"],
  "resume_rewrites": [
    {{
      "original": "项目经历中的原句或原始表达",
      "rewritten": "更适合简历的改写版本，要具体、有个人贡献、有技术方案或指标",
      "reason": "为什么这样改"
    }}
  ]
}}

提问方向：{question_focus or "综合项目深挖"}
项目经历：
{project_text[:4000]}

训练记录：
{transcript}
""".strip()


def build_paradigm_answer_prompt(
    question: str,
    user_answer: str,
    related_context: str,
    target_role: str,
) -> str:
    return f"""
请以严格但有教学能力的大厂技术面试官视角，为下面这个面试问题生成一个“范式回答”。

要求：
1. 不要给空泛模板，要结合问题、候选人的回答和上下文生成可学习的示范。
2. 范式回答必须短，符合真实面试现场口头回答节奏，sample_answer 不超过 5 句话。
3. answer_structure 不超过 4 点，每一点用短语表达，不要写长段落。
4. 范式回答优先覆盖：结论、个人职责、关键方案/取舍、结果或复盘；不要把所有细节都塞进去。
5. 如果候选人原回答缺少关键细节，可以补足一种合理表达，但不要编造具体不存在的数字；没有数字时用“可以补充某个可验证指标”提示。
6. 口吻要像优秀候选人在真实面试中的简洁回答，不要像论文、说明书或长篇复盘。
7. why_better 不超过 2 句话，common_pitfalls 不超过 3 条。
8. 只输出 JSON，不要输出 Markdown。

输出格式：
{{
  "answer_structure": ["结构点1", "结构点2"],
  "sample_answer": "一段完整范式回答",
  "why_better": "为什么这个回答更好",
  "common_pitfalls": ["常见坑1", "常见坑2"]
}}

目标岗位：{target_role or "技术实习生"}
面试问题：
{question}

候选人原回答：
{user_answer or "用户没有提供有效回答。"}

相关上下文：
{related_context[:4000]}
""".strip()


def build_summary_prompt(transcript: str) -> str:
    return f"""
请以严格的大厂技术面试官视角，根据以下模拟面试记录输出 JSON：
要求评价具体、有压迫感但公平，指出候选人的真实短板，避免泛泛鼓励。
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
