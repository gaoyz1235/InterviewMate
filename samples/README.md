# 测试样例说明

本目录用于手动体验 AI 面试模拟器，不是自动化测试。

## 简历样例

- `resume_backend_intern.txt`：后端开发实习方向，适合测试项目深挖、缓存、接口设计。
- `resume_frontend_intern.txt`：前端开发实习方向，适合测试组件设计、状态管理、性能优化。
- `resume_algorithm_research.txt`：算法/机器学习方向，适合测试模型选择、指标设计、实验复盘。

## 回答样例

- `sample_answers.md`：包含较短回答、中等回答、完整回答和超时场景回答。

## 使用方式

1. 打开页面后，把任意 `resume_*.txt` 内容粘贴到“脱敏简历”输入框。
2. 填写目标公司、岗位和面试时长。
3. 开始面试后，从 `sample_answers.md` 中复制回答进行手动体验。
4. 查看 `logs/app.log`，确认简历分析、面试规划、追问判断和总结的 LLM 调用情况。
