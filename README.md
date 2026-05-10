# AI Interview Simulator

面向互联网大厂技术实习的一面模拟器。用户上传 PDF 或粘贴脱敏简历后，系统根据目标公司、岗位和面试时长生成模拟面试问题，后续会补充连续追问、评分反馈、简历修改建议和练习计划。

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

## 下一步

1. 接入 LLM API，替换当前规则生成的首问。
2. 实现回答提交、追问判断和 3 分钟计时记录。
3. 增加结束页：问答记录、四维评分、简历修改建议、练习计划。
