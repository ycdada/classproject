# 数据结构智能出卷完善版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将本仓库完善为严格符合基础需求七条的纯教师端出卷系统，前端换为 React，后端以考查范围确认 + 题目草稿替换静默补题，并让当前源码与 `原文档/` 两套基线都过 30% 差异门。

**Architecture:** 出卷主线是 `出卷需求 → ScopeBuilder.propose → 教师确认考查范围 → PaperAssembler.assemble → 试卷 + 题目草稿`。课程材料库与课程知识树仍按材料维护。教学助手只走一条 LangGraph 缝，组卷不得跳过考查范围确认。运行应用压到仓库根 `backend/` + `frontend/`。

**Tech Stack:** React 18, TypeScript, Vite, Ant Design 5, React Router 6, Zustand, Axios, FastAPI, SQLAlchemy async, aiosqlite, ChromaDB, DeepSeek Chat, sentence-transformers `BAAI/bge-small-zh-v1.5`, LangGraph, python-docx, python-pptx, reportlab, pytest

**Spec:** `.scratch/ds-exam-v3/spec.md`（副本 `docs/superpowers/specs/2026-09-16-ds-exam-v3.md`）

## Global Constraints

- 领域词只使用 `CONTEXT.md`：教师、课程材料库、材料、知识节点、知识树、解题步骤、出卷需求、考查范围、组卷、组卷结果、题目、题目草稿、题库、试卷、审核、教学助手、差异基线。
- 前端运行栈是 React 18 + TypeScript + Vite + Ant Design 5 + React Router + Zustand；运行中的 frontend 不得残留 `.vue`。
- 后端保持 FastAPI + LangGraph + Chroma + DeepSeek；Python 3.10 可运行。
- 组卷前必须有 status=`confirmed` 的考查范围；PaperAssembler 不得向 questions 表插入行。
- 题目草稿未 accept 不得出现在试卷上，也不得写入题库。
- 基础需求七条必须可演示，缺一条即任务失败。
- 差异门：`python scripts/measure_diff.py` 对源码 churn、模块替换、学术文档重写均 ≥ 0.30，且观感清单全过。
- 课件 PPT 保留在 `数据结构资料/`；允许重建 SQLite / Chroma / checkpoints。
- 不要提交 `node_modules/`、`.venv/`、`__pycache__/`、Chroma 二进制。

---

## File Structure Map

冻结后删除运行路径 `project1.3/`。新树：

```
/
  CONTEXT.md
  AGENTS.md
  README.md
  .env.example
  docs/adr/0001–0006
  docs/superpowers/specs/2026-09-16-ds-exam-v3.md
  docs/superpowers/plans/2026-09-16-ds-exam-v3-refactor.md
  .scratch/ds-exam-v3/spec.md
  baselines/v2-source/          # 冻结的旧源码（只读）
  baselines/original-docs/      # 冻结的原文档（只读）
  原文档/                       # 重写后的学术文档（同名文件）
  数据结构资料/                 # 课件 PPT，不改
  scripts/measure_diff.py
  scripts/test_measure_diff.py
  backend/
    requirements.txt            # 现有依赖 + pytest + httpx
    app/main.py
    app/config.py
    app/database.py
    app/models/{material,knowledge,question,exam,scope,draft}.py
    app/schemas/{...}
    app/routers/{materials,knowledge,questions,scopes,exams,drafts,chat}.py
    app/services/{file_parser,llm_adapter,rag,question_service,
                  scope_builder,question_author,paper_assembler,
                  draft_service,chat 删除 v1,
                  docx_export,exam_export,answer_sheet}.py
    agent_v2/{state,nodes,tools,graph}.py
    tests/{conftest.py,test_scope_builder.py,test_paper_assembler.py,
           test_draft_service.py,test_generate_guard.py}
  frontend/
    package.json                # react 18, antd 5, react-router-dom, zustand, axios, typescript, vite
    src/main.tsx
    src/App.tsx
    src/layouts/AppLayout.tsx
    src/types/index.ts
    src/api/{client,materials,knowledge,questions,scopes,exams,drafts,chat}.ts
    src/pages/{Dashboard,Materials,MaterialDetail,KnowledgeTree,
               QuestionBank,ExamWizard,ExamList,ExamPreview,
               Drafts}.tsx
    src/components/{ScopeTree,QuestionBlock,ChatDock}.tsx
```

删除：`app/routers/chat_v2.py`（逻辑并入 `chat.py`）、`app/services/exam_generator.py`（由 `paper_assembler.py` 取代）、`frontend` 全部 Vue 源。

---

## 基础需求 → 任务

| # | 基础需求 | 任务 |
|---|---------|------|
| 1 | 上传教案/PPT/大纲，形成课程材料库 | T3, T13 |
| 2 | 抽出知识点、术语、定义、解题步骤、教学重点 | T3, T14 |
| 3 | 输入教学进度、考试范围、题型、难度、重点方向 | T4, T15 |
| 4 | 筛选组织生成本次考查范围 | T5, T6 |
| 5 | 树状展示，教师审核修改确认 | T6, T15 |
| 6 | 按确认范围 + 材料讲解方式组卷 | T8, T9 |
| 7 | 预览、修改、保存、导出 | T16, T17 |

---

### Task 1: 冻结基线并落地度量脚本

**Files:**
- Create: `baselines/v2-source/`（复制旧应用源，排除 node_modules/dist/__pycache__/chroma 二进制）
- Create: `baselines/original-docs/`（复制当前 `原文档/` 全文）
- Create: `scripts/measure_diff.py`
- Create: `scripts/test_measure_diff.py`
- Create: `scripts/module_inventory.json`

**Interfaces:**
- Consumes: 无
- Produces: `measure_diff(v2_source, original_docs, new_source, new_docs) -> dict` with keys `source_churn`, `module_change`, `doc_rewrite`, `pass`

- [ ] **Step 1: 冻结基线**

```powershell
New-Item -ItemType Directory -Force baselines\v2-source, baselines\original-docs | Out-Null
robocopy "project1.3\project1.3\project1\backend" "baselines\v2-source\backend" /E /XD __pycache__ .venv data uploads
robocopy "project1.3\project1.3\project1\frontend\src" "baselines\v2-source\frontend-src" /E
Copy-Item "project1.3\project1.3\project1\frontend\package.json" "baselines\v2-source\frontend-package.json"
robocopy "原文档" "baselines\original-docs" /E
```

在 `baselines/v2-source/frontend-src` 确认有 `App.vue`。在 `baselines/original-docs` 确认四件套都在。

- [ ] **Step 2: 写模块清单**

`scripts/module_inventory.json`：

```json
{
  "modules": [
    "material_kind",
    "knowledge_extract",
    "scope_builder",
    "exam_scope_persistence",
    "paper_assembler",
    "question_draft",
    "draft_accept",
    "chat_graph",
    "chat_http",
    "exam_wizard_ui",
    "knowledge_tree_ui",
    "material_ui",
    "question_bank_ui",
    "exam_preview_export_ui",
    "assistant_ui",
    "doc_plan",
    "doc_midterm",
    "doc_dev",
    "doc_slides"
  ],
  "changed": []
}
```

实现过程中每完成一个模块，把名字写入 `changed`。门槛：`len(changed)/len(modules) >= 0.30`。

- [ ] **Step 3: 写失败测试**

```python
# scripts/test_measure_diff.py
from pathlib import Path
import tempfile, shutil
from measure_diff import measure_diff, extract_paragraphs

def test_identical_trees_fail_threshold():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "old" / "a.py").parent.mkdir(parents=True)
        (d / "old" / "a.py").write_text("print(1)\n", encoding="utf-8")
        shutil.copytree(d / "old", d / "new")
        (d / "docs_old" / "a.txt").parent.mkdir(parents=True)
        (d / "docs_old" / "a.txt").write_text("hello world\n" * 20, encoding="utf-8")
        shutil.copytree(d / "docs_old", d / "docs_new")
        r = measure_diff(d / "old", d / "docs_old", d / "new", d / "docs_new",
                         inventory={"modules": ["a", "b", "c"], "changed": []})
        assert r["source_churn"] < 0.3
        assert r["pass"] is False
```

- [ ] **Step 4: 实现度量**

```python
# scripts/measure_diff.py
from __future__ import annotations
from pathlib import Path
import hashlib, json, re, zipfile, argparse

SRC_SUFFIX = {".py", ".ts", ".tsx", ".js", ".vue", ".css", ".md"}
SKIP_PARTS = {"node_modules", "dist", "__pycache__", ".venv", "chroma"}

def iter_files(root: Path, suffixes=None):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        if suffixes and p.suffix.lower() not in suffixes:
            continue
        yield p

def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def source_churn(old: Path, new: Path) -> float:
    old_bytes = {file_hash(p): p.stat().st_size for p in iter_files(old, SRC_SUFFIX)}
    new_hashes = {file_hash(p) for p in iter_files(new, SRC_SUFFIX)}
    total = sum(old_bytes.values()) or 1
    survived = sum(sz for h, sz in old_bytes.items() if h in new_hashes)
    return 1.0 - survived / total

def extract_docx_paragraphs(path: Path) -> list[str]:
    from xml.etree import ElementTree as ET
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras = []
    for p in root.findall(".//w:p", ns):
        text = "".join((t.text or "") for t in p.findall(".//w:t", ns)).strip()
        if text:
            paras.append(text)
    return paras

def extract_pptx_text(path: Path) -> list[str]:
    from xml.etree import ElementTree as ET
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    paras = []
    with zipfile.ZipFile(path) as z:
        slides = sorted(n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        for name in slides:
            root = ET.fromstring(z.read(name))
            for t in root.findall(".//a:t", ns):
                if t.text and t.text.strip():
                    paras.append(t.text.strip())
    return paras

def extract_paragraphs(path: Path) -> list[str]:
    if path.suffix.lower() == ".docx":
        return extract_docx_paragraphs(path)
    if path.suffix.lower() == ".pptx":
        return extract_pptx_text(path)
    return [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]

def doc_rewrite(old_dir: Path, new_dir: Path) -> float:
    targets = [
        "数据结构出卷系统-项目计划书.docx",
        "数据结构智能出卷系统_中期报告.docx",
        "开发文档.docx",
        "摸鱼小组-《数据结构》智能出卷系统.pptx",
    ]
    scores = []
    for name in targets:
        op, np = old_dir / name, new_dir / name
        if not op.exists() or not np.exists():
            scores.append(1.0)
            continue
        old_p, new_p = extract_paragraphs(op), extract_paragraphs(np)
        old_set, new_set = set(old_p), set(new_p)
        if not old_set:
            scores.append(1.0)
            continue
        scores.append(1.0 - len(old_set & new_set) / len(old_set))
    return min(scores) if scores else 0.0

def measure_diff(old_src, old_docs, new_src, new_docs, inventory=None):
    if inventory is None:
        inventory = json.loads(Path("scripts/module_inventory.json").read_text(encoding="utf-8"))
    modules = inventory["modules"]
    changed = set(inventory.get("changed", []))
    result = {
        "source_churn": source_churn(Path(old_src), Path(new_src)),
        "module_change": (len(changed) / len(modules)) if modules else 0.0,
        "doc_rewrite": doc_rewrite(Path(old_docs), Path(new_docs)),
    }
    result["pass"] = all(result[k] >= 0.30 for k in ("source_churn", "module_change", "doc_rewrite"))
    return result

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--old-src", default="baselines/v2-source")
    p.add_argument("--old-docs", default="baselines/original-docs")
    p.add_argument("--new-src", default=".")
    p.add_argument("--new-docs", default="原文档")
    args = p.parse_args()
    r = measure_diff(args.old_src, args.old_docs, args.new_src, args.new_docs)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    raise SystemExit(0 if r["pass"] else 1)
```

度量时 `--new-src` 只应扫描 `backend/` 与 `frontend/src`（可在 `iter_files` 增加 root 过滤：若 root 为仓库根，仅进入这两个目录）。实现时加上该过滤，避免把 `baselines/` 算进新树。

- [ ] **Step 5: 跑测试**

Run: `cd scripts; python -m pytest test_measure_diff.py -v`  
Expected: `test_identical_trees_fail_threshold` PASS

- [ ] **Step 6: Commit**

```bash
git add baselines scripts
git commit -m "chore: freeze v2 baselines and add 30% difference gate"
```

---

### Task 2: 压平仓库并复制后端

**Files:**
- Create: `backend/`（从 `project1.3/project1.3/project1/backend` 复制 app/ agent_v2/ requirements.txt，不含 data/uploads/__pycache__）
- Modify: `backend/app/main.py` CORS 仍允许 `http://localhost:5173`
- Create: `backend/tests/conftest.py`
- Create: `backend/.env.example`

**Interfaces:**
- Consumes: 旧后端代码
- Produces: 根目录可启动的 FastAPI 应用

- [ ] **Step 1: 复制**

```powershell
robocopy "project1.3\project1.3\project1\backend\app" "backend\app" /E /XD __pycache__
robocopy "project1.3\project1.3\project1\backend\agent_v2" "backend\agent_v2" /E /XD __pycache__
Copy-Item "project1.3\project1.3\project1\backend\requirements.txt" "backend\requirements.txt"
```

在 `requirements.txt` 追加：

```
pytest>=8.0.0
httpx>=0.24.0
```

- [ ] **Step 2: conftest**

```python
# backend/tests/conftest.py
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test.db")
```

- [ ] **Step 3: 冒烟**

Run: `cd backend; python -c "from app.main import app; print(app.title)"`  
Expected: `DS Exam System API`

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "chore: flatten backend to repo root"
```

---

### Task 3: 材料种类 + 解题步骤（基础需求 1–2）

**Files:**
- Modify: `backend/app/models/material.py`
- Modify: `backend/app/models/knowledge.py`
- Modify: `backend/app/schemas/material.py`
- Modify: `backend/app/schemas/knowledge.py`
- Modify: `backend/app/routers/materials.py`
- Modify: `backend/app/services/llm_adapter.py` `extract_knowledge_tree`
- Modify: `backend/app/routers/knowledge.py` 保存 `solution_steps`

**Interfaces:**
- Consumes: 现有 Material / KnowledgeNode
- Produces: `Material.kind: str`；`KnowledgeNode.solution_steps: str | None`；提取 JSON 每 point 含 `solution_steps`

- [ ] **Step 1: 模型**

`Material` 增加：

```python
kind: Mapped[str] = mapped_column(String(20), default="other", comment="lecture_notes/slides/syllabus/other")
```

`KnowledgeNode` 增加：

```python
solution_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: 上传接口**

`POST /api/materials/upload` 增加表单字段 `kind`，默认 `other`。若扩展名为 pptx 且未传 kind，默认 `slides`。允许的 kind 集合：`lecture_notes`, `slides`, `syllabus`, `other`。非法 kind 返回 400。

- [ ] **Step 3: 提取 prompt**

将 `extract_knowledge_tree` 的 point 对象改为：

```json
{
  "name": "知识点名称",
  "definition": "概念定义原文或紧贴原文的转述",
  "key_terms": ["术语"],
  "solution_steps": "材料中的解题或算法步骤；没有则空字符串",
  "teaching_emphasis": "教学重点"
}
```

规则增加：不得编造解题步骤；材料没有则空字符串。落库时写入 `KnowledgeNode.solution_steps`。

- [ ] **Step 4: 把 material_kind 与 knowledge_extract 写入 `scripts/module_inventory.json` 的 changed**

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/app/schemas backend/app/routers backend/app/services/llm_adapter.py scripts/module_inventory.json
git commit -m "feat: material kinds and solution_steps on knowledge points"
```

---

### Task 4: 出卷需求字段（基础需求 3）

**Files:**
- Modify: `backend/app/schemas/exam.py` `ExamRequirements`

**Interfaces:**
- Produces:

```python
class ExamRequirements(BaseModel):
    title: str
    duration: int = 120
    total_score: int = 100
    teaching_progress: str = ""
    exam_scope: str = ""
    focus_notes: str = ""
    material_ids: list[int] = []
    knowledge_node_ids: list[int] = []  # 仅作备用；考查范围确认后以 scope 为准
    question_distribution: dict
    difficulty_distribution: dict
```

- [ ] **Step 1: 改 schema，任何仍调用 `ExamRequirements` 的地方补默认空字符串，保证旧测试数据能构造。**
- [ ] **Step 2: Commit** `feat: exam demand includes progress and scope text`

---

### Task 5: 考查范围模型与 ScopeBuilder（基础需求 4）

**Files:**
- Create: `backend/app/models/scope.py`
- Create: `backend/app/schemas/scope.py`
- Create: `backend/app/services/scope_builder.py`
- Create: `backend/tests/test_scope_builder.py`
- Modify: `backend/app/models/__init__.py` 导出新模型
- Modify: `backend/app/models/exam.py` 增加 `scope_id`

**Interfaces:**
- Consumes: `KnowledgeNode`, `ExamRequirements`
- Produces:

```python
class ExamScope(Base):
    __tablename__ = "exam_scopes"
    id: int
    status: str          # proposed | confirmed
    demand_json: dict
    created_at: datetime

class ExamScopeNode(Base):
    __tablename__ = "exam_scope_nodes"
    id, scope_id, parent_id, source_node_id
    sort_order, name, node_type
    definition, key_terms, teaching_emphasis, solution_steps
    included: bool       # default True

class ScopeBuilder:
    def __init__(self, db: AsyncSession, llm: LLMAdapter | None = None): ...
    async def propose(self, demand: dict) -> ExamScope: ...
```

`propose` 行为：从 `demand["material_ids"]` 对应知识树取节点（空则取全部材料）；用教学进度、考试范围、重点方向过滤。无 LLM 时用子串匹配 `name/definition/teaching_emphasis`。保留章—节—点父子关系。结果 status=`proposed`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_scope_builder.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base
from app.models.material import Material
from app.models.knowledge import KnowledgeNode
from app.services.scope_builder import ScopeBuilder

@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s

@pytest.mark.asyncio
async def test_propose_keeps_matching_chapter_only(db):
    m = Material(filename="ch5.pptx", file_type="pptx", file_path="x", kind="slides")
    db.add(m)
    await db.flush()
    ch = KnowledgeNode(material_id=m.id, parent_id=None, name="第5章 树和二叉树", node_type="chapter", sort_order=0)
    db.add(ch)
    await db.flush()
    pt = KnowledgeNode(material_id=m.id, parent_id=ch.id, name="先序遍历", node_type="point",
                       definition="根左右", teaching_emphasis="递归", solution_steps="访根→左→右", sort_order=0)
    other = KnowledgeNode(material_id=m.id, parent_id=None, name="第8章 排序", node_type="chapter", sort_order=1)
    db.add_all([pt, other])
    await db.commit()
    scope = await ScopeBuilder(db).propose({
        "title": "单元测验",
        "teaching_progress": "已讲完树",
        "exam_scope": "二叉树遍历",
        "focus_notes": "先序遍历",
        "material_ids": [m.id],
        "question_distribution": {"choice": 2},
        "difficulty_distribution": {"3": 100},
        "duration": 60,
        "total_score": 10,
    })
    from sqlalchemy import select
    from app.models.scope import ExamScopeNode
    names = {n.name for n in (await db.execute(select(ExamScopeNode).where(ExamScopeNode.scope_id == scope.id))).scalars()}
    assert "先序遍历" in names
    assert "第8章 排序" not in names
    assert scope.status == "proposed"
```

- [ ] **Step 2: Run** `cd backend; python -m pytest tests/test_scope_builder.py -v`  
Expected: FAIL `ScopeBuilder` not defined

- [ ] **Step 3: 实现 ScopeBuilder**（无 LLM 的匹配规则必须让上测试通过：若 demand 文本与节点 name/definition/emphasis 任一命中则保留该点及其祖先；章节点仅当有后代被保留才保留。）

- [ ] **Step 4: Run 测试 PASS**

- [ ] **Step 5: inventory changed 加入 `scope_builder`, `exam_scope_persistence`；Commit** `feat: exam scope builder proposes a reviewable tree`

---

### Task 6: 考查范围 HTTP + 确认（基础需求 5）

**Files:**
- Create: `backend/app/routers/scopes.py`
- Modify: `backend/app/main.py` include router
- Create: `backend/tests/test_generate_guard.py`（本任务先写 confirm，generate 守卫在 T9 补全）

**Interfaces:**
- `POST /api/scopes/propose` body=`ExamRequirements` → `{id, status, tree}`
- `GET /api/scopes/{id}` → `{id, status, demand, tree}`
- `PUT /api/scopes/{id}/nodes/{node_id}` body 可改 name/definition/key_terms/teaching_emphasis/solution_steps/included
- `POST /api/scopes/{id}/nodes` 教师新增节点（parent_id 可空）
- `DELETE /api/scopes/{id}/nodes/{node_id}`
- `POST /api/scopes/{id}/confirm` → status=confirmed；已确认后再 PUT 节点返回 409

tree JSON 与知识树相同：嵌套 `children`。

- [ ] **Step 1: 实现路由并注册 prefix `/scopes`**
- [ ] **Step 2: 手测或 pytest：propose → 改名 → confirm → 再 PUT 得 409**
- [ ] **Step 3: Commit** `feat: exam scope review and confirm API`

---

### Task 7: 题目草稿模型与 DraftService

**Files:**
- Create: `backend/app/models/draft.py`
- Create: `backend/app/schemas/draft.py`
- Create: `backend/app/services/draft_service.py`
- Create: `backend/app/routers/drafts.py`
- Create: `backend/tests/test_draft_service.py`
- Modify: `backend/app/main.py`

**Interfaces:**

```python
class QuestionDraft(Base):
    __tablename__ = "question_drafts"
    id, type, difficulty, chapter, knowledge_point_ids
    content, options, answer, explanation
    status: str          # pending | accepted | rejected
    exam_scope_id: int | None
    created_at

class DraftService:
    async def create_many(self, items: list[dict], exam_scope_id=None) -> list[QuestionDraft]
    async def accept(self, draft_id: int) -> Question   # 调 QuestionService.create_question, source="manual" 不允许 "ai_generated"
    async def reject(self, draft_id: int) -> None
    async def update(self, draft_id: int, data: dict) -> QuestionDraft  # 仅 pending
```

source 在 accept 时用 `manual`（教师已确认）。不要引入 `ai_generated` 作为题库来源。

- [ ] **Step 1: 测试 accept 使 questions 表 +1 且 draft.status=accepted；reject 不增加 questions。**
- [ ] **Step 2: 实现并让测试通过。**
- [ ] **Step 3: 路由 `GET /api/drafts?status=pending`、`PUT /api/drafts/{id}`、`POST /api/drafts/{id}/accept`、`POST /api/drafts/{id}/reject`**
- [ ] **Step 4: inventory `question_draft`, `draft_accept`；Commit** `feat: question drafts accepted only by teacher`

---

### Task 8: PaperAssembler（基础需求 6）

**Files:**
- Create: `backend/app/services/question_author.py`
- Create: `backend/app/services/paper_assembler.py`
- Create: `backend/tests/test_paper_assembler.py`
- Delete after switch: `backend/app/services/exam_generator.py`（T9 切换后删除）

**Interfaces:**

```python
@dataclass
class AssembleResult:
    questions: list[dict]   # {question_id, score, sort_order, type, content, ...}
    drafts: list[dict]
    shortfall: dict[str, int]
    summary: str

class QuestionAuthor(Protocol):
    async def propose(self, spec: dict, context: str) -> list[dict]: ...

class FakeAuthor:
    async def propose(self, spec, context):
        n = spec["count"]
        return [{"type": spec["type"], "difficulty": 3, "chapter": "", "knowledge_point_ids": [],
                 "content": f"草稿{i}", "options": {"A": "1", "B": "2", "C": "3", "D": "4"} if spec["type"]=="choice" else None,
                 "answer": "A" if spec["type"]=="choice" else "略", "explanation": ""} for i in range(n)]

class PaperAssembler:
    def __init__(self, db, rag, llm, author: QuestionAuthor, drafts: DraftService): ...
    async def assemble(self, demand: dict, scope: ExamScope) -> AssembleResult: ...
```

规则：
1. `scope.status != "confirmed"` 时 raise `ValueError("scope_not_confirmed")`
2. 用确认范围内 included=True 的点拼接 context（定义、术语、解题步骤、教学重点）
3. 按题型 RAG 检索题库，只选已存在题目
4. 数量不足时 `author.propose` + `drafts.create_many`，questions 表行数不变
5. 分数归一到 total_score（沿用现 `_normalize_scores` 逻辑，把它挪到 `paper_assembler.py`）

- [ ] **Step 1: 失败测试**

```python
@pytest.mark.asyncio
async def test_shortfall_creates_drafts_not_questions(db):
    # 建 1 道 choice 题目 + confirmed scope
    # demand 要 3 道 choice
    before = (await db.execute(select(func.count(Question.id)))).scalar()
    result = await PaperAssembler(db, rag=FakeRag([existing_id]), llm=None, author=FakeAuthor(), drafts=DraftService(db)).assemble(demand, scope)
    after = (await db.execute(select(func.count(Question.id)))).scalar()
    assert after == before
    assert len(result.questions) == 1
    assert len(result.drafts) == 2
    assert result.shortfall["choice"] == 2

@pytest.mark.asyncio
async def test_assemble_rejects_unconfirmed_scope(db):
    scope.status = "proposed"
    with pytest.raises(ValueError, match="scope_not_confirmed"):
        await assembler.assemble(demand, scope)
```

`FakeRag` 实现 `search` 返回给定 id。测试文件内提供最小 FakeRag，不要 mock 私有方法。

- [ ] **Step 2: Run 确认 FAIL → 实现 → PASS**
- [ ] **Step 3: inventory `paper_assembler`；Commit** `feat: assemble papers from confirmed scope without silent bank writes`

---

### Task 9: 组卷 API 接到确认后的装配

**Files:**
- Modify: `backend/app/routers/exams.py` `POST /generate`
- Modify: `backend/tests/test_generate_guard.py`
- Delete: `backend/app/services/exam_generator.py`
- Modify: 所有 `ExamGenerator` import 改为 `PaperAssembler`
- Modify: `verify` / `regenerate`：不足时写草稿，不写题库

**Interfaces:**
- `POST /api/exams/generate` body 增加必填 `scope_id: int`
- 若 scope 不存在 404；未确认 400 `{detail: "scope_not_confirmed"}`
- 成功：创建 Exam（`scope_id`、`requirements_json`、`knowledge_snapshot_json`=范围树），写入 ExamQuestion（仅 result.questions），返回

```json
{"exam_id": 1, "question_count": 10, "drafts": [...], "shortfall": {"fill": 2}, "summary": "..."}
```

无题目且无草稿时 400。

- [ ] **Step 1: pytest：proposed scope → 400；confirmed → 200 且 questions 表不因 shortfall 增加**
- [ ] **Step 2: 实现；删除 ExamGenerator**
- [ ] **Step 3: Commit** `feat: generate requires confirmed exam scope`

---

### Task 10: 单一 LangGraph 教学助手

**Files:**
- Modify: `backend/agent_v2/state.py` 增加 `scope_id`, `scope_status`
- Modify: `backend/agent_v2/nodes.py` 增加 `propose_scope_node`；`generate_node` 改为先提出范围
- Modify: `backend/agent_v2/graph.py`
- Modify: `backend/agent_v2/tools.py`
- Replace: `backend/app/routers/chat.py` 用现 `chat_v2.py` 内容，前缀改为 `/chat`
- Delete: `backend/app/routers/chat_v2.py`
- Modify: `backend/app/main.py` 只注册一份 chat router
- Delete or stop importing: `backend/app/services/chat_service.py` 的旧 process_message 路径（TOOLS 定义可保留给 router prompt）

**Interfaces:**
- Graph: START→router；search/knowledge→chat→END；generate_exam→propose_scope→scope_review(interrupt)→assemble→paper_review(interrupt)→chat→END
- SSE 事件：`intent`, `tool_call`, `scope_pending`, `review_pending`, `text`, `done`, `error`
- `scope_pending` data: `{scope_id, tree, message}`
- resume: `{kind: "scope", confirmed: true, scope_id}` 或 `{kind: "paper", approved: true}`

- [ ] **Step 1: 实现节点。propose_scope_node 调 ScopeBuilder.propose。assemble 调 PaperAssembler，未确认则 interrupt。**
- [ ] **Step 2: `POST /api/chat` 与现 v2 相同的 thread_id / resume 形状，并识别 `kind`。**
- [ ] **Step 3: inventory `chat_graph`, `chat_http`；Commit** `feat: single LangGraph assistant with scope interrupt`

---

### Task 11: React 脚手架

**Files:**
- Create: `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/vite-env.d.ts`

`package.json` dependencies：

```json
{
  "name": "ds-exam-frontend",
  "private": true,
  "version": "0.3.0",
  "type": "module",
  "scripts": {"dev": "vite", "build": "tsc -b && vite build", "preview": "vite preview"},
  "dependencies": {
    "antd": "^5.27.0",
    "@ant-design/icons": "^5.6.0",
    "axios": "^1.18.1",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.30.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0"
  }
}
```

`vite.config.ts` 与旧配置一样把 `/api` 代理到 `http://localhost:8000`。

`main.tsx` 沿用旧 `waitForBackend` 逻辑（请求 `/api/health`）。

- [ ] **Step 1: `npm install` 后 `npm run build` 在空 App 上通过。**
- [ ] **Step 2: Commit** `feat: scaffold React 18 + Ant Design frontend`

---

### Task 12: 布局、类型、API 客户端

**Files:**
- Create: `frontend/src/layouts/AppLayout.tsx`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/*.ts`
- Modify: `frontend/src/App.tsx` 路由

导航（中文标签与现系统一致，仅加「草稿」）：首页、材料、知识树、题库、组卷、试卷、草稿。

路由：

```
/dashboard
/materials
/materials/:id
/knowledge/:materialId
/questions
/exams/create
/exams
/exams/:id
/exams/:id/review
/drafts
```

`types/index.ts` 必须包含 `Material`, `KnowledgeNode`, `ExamDemand`, `ExamScope`, `ExamScopeNode`, `Question`, `QuestionDraft`, `Exam`, `AssembleResponse`。`ExamDemand` 字段与 Task 4 schema 同名。

API 模块每个函数直接对应后端路径，timeout 组卷 300000ms。`chat.ts` 只实现 LangGraph SSE：事件 `text|tool_call|scope_pending|review_pending|done|error`，请求体 `{message, thread_id, resume}`。

Ant Design 主题 token：`colorPrimary: #0E7C86`（保留现强调色，但组件全部是 antd，布局改为顶栏+侧栏）。

- [ ] **Step 1: 写齐类型与 API，空页面占位也能切路由。**
- [ ] **Step 2: inventory 暂不标 UI；Commit** `feat: React layout, types, and API clients`

---

### Task 13: 材料页（基础需求 1）

**Files:**
- Create: `frontend/src/pages/Materials.tsx`, `MaterialDetail.tsx`
- 行为对照：`baselines/v2-source/frontend-src/views/teacher/MaterialUpload.vue`, `MaterialDetail.vue`

必须：上传时选择种类（教案/PPT/大纲/其他）；列表显示种类；详情显示解析正文；删除。

- [ ] **Step 1: 实现。Naive `n-upload` → antd `Upload`；`n-table` → `Table`。**
- [ ] **Step 2: inventory `material_ui`；Commit** `feat: React course material library`

---

### Task 14: 课程知识树（基础需求 2、5 的课程侧）

**Files:**
- Create: `frontend/src/pages/KnowledgeTree.tsx`
- Create: `frontend/src/components/ScopeTree.tsx`（课程树与考查范围树共用，用 antd `Tree`）
- 行为对照：`baselines/v2-source/frontend-src/views/teacher/KnowledgeTree.vue`

必须：提取/重新提取；树展示；详情含定义、术语、**解题步骤**、教学重点；编辑保存；不能再把「解题步骤」丢掉。

- [ ] **Step 1: 实现。**
- [ ] **Step 2: inventory `knowledge_tree_ui`；Commit** `feat: React knowledge tree with solution steps`

---

### Task 15: 组卷向导步骤 1–2（基础需求 3–5）

**Files:**
- Create: `frontend/src/pages/ExamWizard.tsx`

三步 `Steps`：出卷需求 → 考查范围 → 试卷。

步骤 1 表单字段（全部必能提交）：试卷名称、时长、总分、**教学进度**、**考试范围**、题型数量、难度分布、重点考查方向、可选材料多选。提交调 `POST /api/scopes/propose`，进入步骤 2。

步骤 2：`ScopeTree` 展示返回树；可改 included、改文案、加节点；按钮「确认考查范围」调 `POST /api/scopes/{id}/confirm`，成功进入步骤 3 并调 generate。

未确认不得调用 generate。

- [ ] **Step 1: 实现两步，步骤 3 先放空态。**
- [ ] **Step 2: inventory `exam_wizard_ui`；Commit** `feat: wizard demand and exam-scope confirmation`

---

### Task 16: 组卷向导步骤 3 + 草稿入口（基础需求 6–7 的生成侧）

**Files:**
- Modify: `frontend/src/pages/ExamWizard.tsx`
- 对照旧向导的预览、换题、改分、排序，但进度文案改为：检索题库 → 装配 → 缺口写入草稿 → 校验。禁止再写「AI 生成题目并入库」。

步骤 3：展示试卷题目；若 `drafts.length>0` 用 `Alert` 说明缺口，并链到 `/drafts`。保存即 generate 已落库的试卷。提供「去预览」跳转 `/exams/:id`。

- [ ] **Step 1: 实现。**
- [ ] **Step 2: Commit** `feat: wizard assembles paper after confirmed scope`

---

### Task 17: 试卷列表、预览、修改、导出（基础需求 7）

**Files:**
- Create: `frontend/src/pages/ExamList.tsx`, `ExamPreview.tsx`
- 对照：`ExamList.vue`, `ExamPreview.vue`, `examreview.vue`
- 预览页必须能改题干/选项/答案/解析/分值/顺序，能导出 docx/pdf/txt、含答案版本、答题卡。保存走现有 PUT。

- [ ] **Step 1: 实现。**
- [ ] **Step 2: inventory `exam_preview_export_ui`；Commit** `feat: React exam preview edit and export`

---

### Task 18: 题库页

**Files:**
- Create: `frontend/src/pages/QuestionBank.tsx`
- 对照 `QuestionBank.vue`：筛选、分页、CRUD、批量导入、语义搜索。不提供「AI 生成题目入库」按钮。

- [ ] **Step 1: 实现。**
- [ ] **Step 2: inventory `question_bank_ui`；Commit** `feat: React question bank`

---

### Task 19: 题目草稿页 + 教学助手

**Files:**
- Create: `frontend/src/pages/Drafts.tsx`
- Create: `frontend/src/components/ChatDock.tsx`
- Modify: `AppLayout` 挂载 ChatDock（右下角抽屉，antd `Drawer`+`FloatButton`）

Drafts：列表 pending；编辑；接受；拒绝。接受成功后题目出现在题库。

ChatDock：只调 `/api/chat`。收到 `scope_pending` 展示「去确认考查范围」按钮（跳转向导并带 `scope_id`）。收到 `review_pending` 展示通过/调整。不要再请求旧的无 thread 的 chat。

Dashboard 统计增加 pending 草稿数。首页对话区可复用 ChatDock 嵌入模式。

- [ ] **Step 1: 实现。**
- [ ] **Step 2: inventory `assistant_ui`；Commit** `feat: drafts inbox and LangGraph chat dock`

---

### Task 20: 前端构建门 + 删除旧 Vue 运行树

**Files:**
- Delete running: `project1.3/`（仅在 baselines 已确认完整之后）
- Modify: `frontend` 确保无 `.vue`

- [ ] **Step 1: `cd frontend; npm run build` 必须成功。**
- [ ] **Step 2: 删除 `project1.3` 运行副本（不要删 `baselines/`）。**
- [ ] **Step 3: Commit** `chore: remove nested Vue app from running tree`

---

### Task 21: 重写学术四件套（基础需求叙事 + 30% 文档门）

**Files:**
- Modify: `原文档/数据结构出卷系统-项目计划书.docx`
- Modify: `原文档/数据结构智能出卷系统_中期报告.docx`
- Modify: `原文档/开发文档.docx`
- Modify: `原文档/摸鱼小组-《数据结构》智能出卷系统.pptx`
- Modify: `原文档/数据结构智能出卷Agent_完善版计划书.md` 改为指向考查范围 + React + 题目草稿，删除「最小改动 / 复用 ExamGenerator」表述

对每一份：不要在旧文件上改几个词。用 python-docx / python-pptx **新建内容后覆盖同名文件**。封面可保留课题名「数据结构智能出卷系统」。

**计划书新大纲（必须用这套标题，与旧「项目组织/沟通机制」拉开）：**
1. 课题与基础需求（逐条映射七条）
2. 用户与对象（教师、课程材料库、考查范围、题目草稿）
3. 技术栈（React 18 + Ant Design 5 + FastAPI + LangGraph）
4. 主线：出卷需求 → 考查范围确认 → 组卷 → 草稿审核 → 导出
5. 差异与验收（两套基线 30%）
6. 风险（模型编造、题库不足、提取空步骤）
7. 交付物

**中期报告新大纲：**
1. 基础需求符合性对照表
2. 新架构（考查范围模块、PaperAssembler、单一教学助手）
3. 前端换栈说明（Vue 废弃原因）
4. 已完成模块与演示路径
5. 差异度量方法与当前数字
6. 待完成与风险

**开发文档新大纲：**
1. 领域词
2. 目录结构
3. 数据模型（含 exam_scopes, question_drafts, solution_steps, kind）
4. HTTP 一览
5. 组卷时序
6. 前端页面与路由
7. 本地运行
8. 测试与差异门

**答辩 PPT 新大纲（不少于 12 页，旧页结构不得复用过半）：**
1. 题目与基础需求
2. 问题：静默补题与无考查范围
3. 目标完善点
4. 总体架构（React / FastAPI）
5. 课程材料库
6. 知识抽取（含解题步骤）
7. 出卷需求
8. 考查范围确认
9. 组卷与题目草稿
10. 教学助手状态机
11. 导出
12. 差异验收
13. 演示
14. 总结

观感清单（Task 23 人工勾）：不得把 Vue 3 / Naive UI 写成现行技术；必须出现「考查范围」「题目草稿」「解题步骤」；架构图与旧文档不同。

- [ ] **Step 1: 用脚本生成四份新文件并覆盖 `原文档/`。**
- [ ] **Step 2: 跑 `python scripts/measure_diff.py` 看 `doc_rewrite`；若 <0.30 继续替换段落，直到过线。**
- [ ] **Step 3: inventory 四个 `doc_*`；Commit** `docs: rewrite academic pack for v3 domain and stack`

---

### Task 22: 工程文档收口

**Files:**
- Modify: `README.md` 按完善版运行方式写准
- Modify: `docs/superpowers` 旧 v2 spec/plan 文首加一行：`Superseded by 2026-09-16-ds-exam-v3`
- Create: `backend/.env.example`（`DEEPSEEK_API_KEY=` `DATABASE_URL=sqlite+aiosqlite:///./data/ds_teaching.db`）

- [ ] **Step 1: 写完。**
- [ ] **Step 2: Commit** `docs: point engineering docs at v3 spec`

---

### Task 23: 验收门（实现 agent 不得跳过）

- [ ] **Step 1: `cd backend; python -m pytest -v` 全部绿。**
- [ ] **Step 2: `cd frontend; npm run build` 成功。**
- [ ] **Step 3: 基础需求走查（启动前后端，按下表点一遍，全部打勾）：**

| # | 操作 | 期望 |
|---|------|------|
| 1 | 上传一份 PPT 种类=PPT，一份 docx 种类=教案 | 课程材料库能列出且种类正确 |
| 2 | 对材料点提取 | 点上能看到定义、术语、解题步骤、教学重点（步骤可空但字段在） |
| 3 | 组卷步骤1 填写教学进度、考试范围、题型、难度、重点 | 能提交 |
| 4 | 系统给出考查范围树 | 树与需求相关，不是空列表或「节点 #id」 |
| 5 | 修改一节点并确认 | 未确认时 generate 失败；确认后进入试卷 |
| 6 | 题型数量大于题库 | 试卷只有题库题；草稿列表出现缺口 |
| 7 | 预览改一题分值并导出 docx | 文件可下载 |

- [ ] **Step 4: `python scripts/measure_diff.py` 退出码 0；打印的三项都 ≥0.30。**
- [ ] **Step 5: 观感清单：** 原文档现行技术是 React；有考查范围和题目草稿专章/专页；不是旧 PPT 换标题。
- [ ] **Step 6: Commit** `chore: v3 acceptance gate green`

---

## Self-Review

**Spec coverage:** 基础需求 1–7 分别落在 T3/T13、T3/T14、T4/T15、T5/T6、T6/T15、T8/T9、T16/T17。题目草稿 T7/T19。换栈 T11–T20。两套 30% T1/T21/T23。单一助手 T10。压平 T2/T20。

**Placeholder scan:** 无 TBD。UI 任务以 baselines 下的 Vue 为行为预言，目标栈与组件映射已写明。

**Type consistency:** `ExamRequirements` / `ExamDemand` 字段名在 schema、ScopeBuilder.propose、前端 types 中相同。`AssembleResult` 与 generate JSON 相同。scope status 只有 `proposed` | `confirmed`。draft status 只有 `pending` | `accepted` | `rejected`。
