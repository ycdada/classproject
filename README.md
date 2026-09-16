# 数据结构智能出卷系统（完善版）

纯教师端。上传教案 / PPT / 大纲，抽出知识树，按出卷需求生成考查范围，确认后组卷，缺口进入题目草稿，导出 Word / PDF。

## 现状与去向

可运行旧树在 `project1.3/project1.3/project1/`。完善版把应用压到仓库根的 `backend/` 与 `frontend/`，前端改为 React 18 + Ant Design 5，后端仍为 FastAPI。

规格：`.scratch/ds-exam-v3/spec.md`  
计划：`docs/superpowers/plans/2026-09-16-ds-exam-v3-refactor.md`  
术语：`CONTEXT.md`

## 本地运行（完善版落地后）

```bash
# 后端
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# .env 中设置 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`。
