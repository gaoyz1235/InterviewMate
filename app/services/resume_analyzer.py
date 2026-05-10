import logging
import re

from app.schemas.interview import ResumeAnalysis, ResumeProject
from app.services.llm_client import LLMClient
from app.services.prompt_builder import build_resume_analysis_prompt

logger = logging.getLogger(__name__)

SKILL_KEYWORDS = [
    "Python",
    "Java",
    "Go",
    "C++",
    "JavaScript",
    "TypeScript",
    "React",
    "Vue",
    "FastAPI",
    "Flask",
    "Django",
    "Spring",
    "MySQL",
    "PostgreSQL",
    "Redis",
    "MongoDB",
    "Docker",
    "Kubernetes",
    "Linux",
    "HTTP",
    "RPC",
    "消息队列",
    "缓存",
    "数据库",
    "算法",
]

RISK_PATTERNS = [
    ("缺少量化结果", r"(优化|提升|降低|减少|加速)(?!.*\d)"),
    ("职责表述可能不清", r"(参与|负责|协助)(?!.*(独立|主导|设计|实现))"),
    ("技术深度可能不足", r"(熟悉|了解|掌握)(?!.*(原理|源码|性能|一致性|并发))"),
]


def analyze_resume(resume_text: str) -> ResumeAnalysis:
    text = resume_text.strip()
    if not text:
        return ResumeAnalysis(
            risks=["简历文本为空，无法基于项目经历追问。"],
            summary="未提供有效简历内容。",
        )

    llm_analysis = _analyze_resume_with_llm(text)
    if llm_analysis:
        logger.info(
            "resume_analyzer.source source=llm projects=%s skills=%s risks=%s",
            len(llm_analysis.projects),
            len(llm_analysis.skills),
            len(llm_analysis.risks),
        )
        return llm_analysis

    logger.info("resume_analyzer.source source=rule")
    return _analyze_resume_by_rule(text)


def _analyze_resume_with_llm(text: str) -> ResumeAnalysis | None:
    client = LLMClient()
    if not client.configured:
        logger.info("resume_analyzer.llm.skip reason=not_configured")
        return None

    data = client.chat_json(
        "你是严格的技术面试简历分析专家，只输出符合要求的 JSON。",
        build_resume_analysis_prompt(text),
        timeout_seconds=120,
    )
    if not data:
        logger.warning("resume_analyzer.llm.empty")
        return None

    try:
        analysis = ResumeAnalysis(
            projects=[ResumeProject(**project) for project in data.get("projects", []) if isinstance(project, dict)],
            skills=_clean_str_list(data.get("skills", [])),
            risks=_clean_str_list(data.get("risks", [])),
            summary=str(data.get("summary") or "").strip(),
        )
    except Exception as exc:
        logger.exception("resume_analyzer.llm.invalid error=%s", exc.__class__.__name__)
        return None

    if not analysis.projects and not analysis.skills and not analysis.summary:
        logger.warning("resume_analyzer.llm.invalid reason=empty_analysis")
        return None
    return analysis


def _analyze_resume_by_rule(text: str) -> ResumeAnalysis:
    projects = _extract_projects(text)
    skills = _extract_skills(text)
    risks = _extract_risks(text, projects, skills)
    summary = _build_summary(projects, skills, risks)
    return ResumeAnalysis(projects=projects, skills=skills, risks=risks, summary=summary)


def _clean_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _extract_projects(text: str) -> list[ResumeProject]:
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    project_lines = [
        line
        for line in lines
        if any(token in line for token in ["项目", "系统", "平台", "网站", "应用", "服务"])
    ]
    selected = project_lines[:3] or lines[:2]
    projects: list[ResumeProject] = []
    for index, line in enumerate(selected, start=1):
        name = _guess_project_name(line, index)
        technologies = _extract_skills(line)
        projects.append(
            ResumeProject(
                name=name,
                description=line[:240],
                technologies=technologies,
                evidence=line,
            )
        )
    return projects


def _guess_project_name(line: str, index: int) -> str:
    match = re.search(r"([\w\u4e00-\u9fff]+(?:项目|系统|平台|网站|应用|服务))", line)
    if match:
        return match.group(1)[:24]
    return f"项目经历 {index}"


def _extract_skills(text: str) -> list[str]:
    normalized = text.lower()
    skills = []
    for keyword in SKILL_KEYWORDS:
        if keyword.lower() in normalized or keyword in text:
            skills.append(keyword)
    return sorted(set(skills), key=skills.index)


def _extract_risks(text: str, projects: list[ResumeProject], skills: list[str]) -> list[str]:
    risks = []
    if not projects:
        risks.append("简历中没有明显项目经历，面试缺少可深挖素材。")
    if len(skills) < 3:
        risks.append("技能关键词偏少，岗位匹配度可能不够明确。")
    for label, pattern in RISK_PATTERNS:
        if re.search(pattern, text):
            risks.append(label)
    if not re.search(r"\d+%?|\d+ms|\d+qps|\d+人|\d+万", text, flags=re.I):
        risks.append("缺少可验证指标，项目结果说服力偏弱。")
    return sorted(set(risks), key=risks.index)[:5]


def _build_summary(projects: list[ResumeProject], skills: list[str], risks: list[str]) -> str:
    project_part = f"识别到 {len(projects)} 段可用于追问的项目/经历"
    skill_part = f"技能关键词：{', '.join(skills[:8])}" if skills else "技能关键词不明显"
    risk_part = f"主要风险：{risks[0]}" if risks else "简历表达较完整"
    return f"{project_part}；{skill_part}；{risk_part}。"
