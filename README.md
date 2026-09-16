# 数据结构智能出卷系统（完善版 v3）

纯教师端《数据结构》出卷系统：上传教案 / PPT / 大纲形成课程材料库，抽取知识树（含**解题步骤**），填写**出卷需求**，系统提出**考查范围**供教师审核确认，确认后**组卷**——只从题库装配，题库缺口产生**题目草稿**，教师确认后才入库；预览修改后导出 Word / PDF / TXT 与答题卡。

主线：`出卷需求 → ScopeBuilder.propose → 教师确认考查范围 → PaperAssembler.assemble → 试卷 + 题目草稿`。未确认考查范围不得组卷；组卷绝不向题库静默写题。

## 目录

```
backend/    FastAPI + SQLAlchemy async + ChromaDB + DeepSeek + LangGraph（agent_v2）
frontend/   React 18 + TypeScript + Vite + Ant Design 5（无 Vue）
scripts/    30% 差异门度量脚本
baselines/  冻结差异基线（v2 源码 + 旧学术文稿，只读）
原文档/     重写后的学术四件套
docs/adr/   六条不可逆架构决策
数据结构资料/  课程课件 PPT（保留可重导入）
```

## 本地运行

```bash
# 后端
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # 填入 DEEPSEEK_API_KEY
.venv\Scripts\uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`（Vite 代理 `/api` 到 8000）。允许重建本地数据：删除 `backend/data/` 与 `backend/checkpoints.db` 后自动重建 SQLite 与 Chroma。

## 测试与验收

```bash
cd backend && .venv\Scripts\python -m pytest -v   # 后端测试全绿
cd frontend && npm run build                       # tsc + vite 构建通过
python scripts/measure_diff.py                     # 三项差异 ≥ 30%，退出码 0
```

## 文档

- 规格：`.scratch/ds-exam-v3/spec.md`（副本 `docs/superpowers/specs/2026-09-16-ds-exam-v3.md`）
- 计划：`docs/superpowers/plans/2026-09-16-ds-exam-v3-refactor.md`
- 领域词：`CONTEXT.md`
- 运行细节：`原文档/开发文档.docx`
