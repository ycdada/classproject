# AGENTS

完善版交接。实现前先读这些文件，再打开计划里的当前任务。

- 领域词：`CONTEXT.md`。只用其中的词：教师、课程材料库、材料、知识节点、知识树、解题步骤、出卷需求、考查范围、组卷、组卷结果、题目、题目草稿、题库、试卷、审核、教学助手、差异基线。
- 不可逆决定：`docs/adr/`。尤其是 React 前端、题目草稿、两套 30%、压平目录、单一 LangGraph、先确认考查范围再组卷。
- 产品合同：`.scratch/ds-exam-v3/spec.md`（副本 `docs/superpowers/specs/2026-09-16-ds-exam-v3.md`）。基础需求七条必须全部可演示。
- 实现步骤：`docs/superpowers/plans/2026-09-16-ds-exam-v3-refactor.md`。按任务顺序，每任务自带测试或构建门。

完成声明前必须：后端 pytest 通过、前端 `npm run build` 通过、`python scripts/measure_diff.py` 三联 ≥30%、基础需求七条走查通过、学术四件套观感像新版。
