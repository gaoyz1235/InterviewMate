# AI Interview Simulator

面向互联网大厂技术实习的一面模拟器。用户上传 PDF 或粘贴脱敏简历后，系统会解析简历、生成面试计划、围绕项目经历追问，并在结束后输出四维评分、简历修改建议和练习计划。

## 技术栈

- Python 3.11+
- FastAPI
- Jinja2
- pypdf
- 原生 HTML/CSS/JavaScript

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

浏览器打开 `http://127.0.0.1:8000`。

## 当前功能

- 上传 PDF 或粘贴脱敏简历文本。
- 填写目标公司、岗位和面试时长。
- 自动提取项目经历、技能关键词和简历风险点。
- 根据常见题型生成面试计划：项目深挖、技术基础、岗位匹配、行为动机。
- 对话页支持题型显示、3 分钟倒计时、回答耗时记录。
- 后端根据回答长度、耗时和弱信号决定追问、换题或结束。
- 结束页展示问答记录、四维评分、暴露问题、简历修改建议和练习建议。

## LLM 配置

不配置模型也可以使用规则兜底完整演示。如需接入 OpenAI 兼容接口，复制 `.env.example` 为 `.env` 并填写：

```text
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
```

## 项目结构

```text
app/
  api/          # HTTP 路由
  core/         # 配置
  schemas/      # 请求与响应模型
  services/     # 简历解析、Prompt、面试流程
  static/       # 前端静态资源
  templates/    # 页面模板
tests/          # 测试
docs/           # 产品文档、Memo、部署说明
```

## 后续优化

1. 增强 LLM 提示词，让简历分析和总结更稳定输出 JSON。
2. 增加 SQLite 持久化，避免服务重启丢失会话。
3. 增加 OCR 服务作为 PDF 文本抽取失败时的增强能力。
