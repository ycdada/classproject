# 数据结构课程辅助教学智能体 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建完整的数据结构教学智能体系统，覆盖教师题库管理、智能组卷导出、学生在线答题自动批改、错题分析与重练的全流程。

**Architecture:** Vue 3 + Naive UI 前端，FastAPI 后端，SQLite + ChromaDB 存储，Ollama 托管微调后的 Qwen2.5-7B 模型做本地推理，BERT-tiny 小模型做知识点/难度辅助标注。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy / ChromaDB / Ollama / Vue 3 / Naive UI / Pinia / Vite

**环境要求:** conda activate yolo8 (已装 CUDA, RTX 4060 8G)

---

## Phase 1: 基础设施 + 题库管理 (MVP 核心)

### Task 1.1: 初始化项目结构

- [ ] 创建所有目录

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/routers backend/app/services backend/app/utils
mkdir -p backend/data backend/training
mkdir -p frontend/src/router frontend/src/stores frontend/src/views/teacher frontend/src/views/student
mkdir -p frontend/src/components frontend/src/api frontend/src/utils
```

- [ ] 创建 `__init__.py` 文件

```bash
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py
touch backend/app/routers/__init__.py backend/app/services/__init__.py backend/app/utils/__init__.py
```

- [ ] 初始化前端 (Vue 3 + Vite)

```bash
cd frontend && npm create vite@latest . -- --template vue
npm install && npm install naive-ui pinia vue-router axios @vicons/ionicons5
npm install -D sass
```

- [ ] 提交

```bash
git add -A && git commit -m "feat: initialize project structure"
```

### Task 1.2: Backend 依赖 + 配置 + 数据库

- [ ] 创建 `backend/requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.35
aiosqlite==0.20.0
pydantic==2.9.0
pydantic-settings==2.5.0
chromadb==0.5.0
sentence-transformers==3.1.0
python-docx==1.1.2
reportlab==4.2.0
openpyxl==3.1.5
httpx==0.27.0
```

- [ ] 创建 `backend/.env.example`

```env
DATABASE_URL=sqlite+aiosqlite:///./data/ds_teaching.db
CHROMA_PATH=./data/chroma
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=ds-teacher-qwen
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

- [ ] 创建 `backend/app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/ds_teaching.db"
    chroma_path: str = "./data/chroma"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "ds-teacher-qwen"
    embedding_model: str = "all-MiniLM-L6-v2"
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

- [ ] 创建 `backend/app/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] 安装依赖并验证

```bash
conda activate yolo8
cd backend && cp .env.example .env && pip install -r requirements.txt
python -c "from app.config import settings; print(settings.database_url)"
```

### Task 1.3: ORM 数据模型 (5 张表)

- [ ] 创建 `backend/app/models/question.py`

```python
import datetime
from sqlalchemy import Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_points: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="manual")
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] 创建 `backend/app/models/exam.py`

```python
import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="draft")
    total_score: Mapped[int] = mapped_column(Integer, default=100)
    duration: Mapped[int] = mapped_column(Integer, default=120)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    questions = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")

class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=5)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    exam = relationship("Exam", back_populates="questions")
```

- [ ] 创建 `backend/app/models/submission.py`

```python
import datetime
from sqlalchemy import Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(50), nullable=False)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graded_by: Mapped[str] = mapped_column(String(10), default="auto")
    ai_feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    submitted_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] 创建 `backend/app/models/mistake.py`

```python
import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class MistakeRecord(Base):
    __tablename__ = "mistake_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(50), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    last_wrong_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] 验证模型导入

```bash
cd backend && python -c "
from app.models.question import Question
from app.models.exam import Exam, ExamQuestion
from app.models.submission import Submission
from app.models.mistake import MistakeRecord
print('All 5 models OK:', Question.__tablename__, Exam.__tablename__, ExamQuestion.__tablename__, Submission.__tablename__, MistakeRecord.__tablename__)
"
```

### Task 1.4: Pydantic Schemas

- [ ] 创建 `backend/app/schemas/question.py` (QuestionCreate, QuestionUpdate, QuestionOut, QuestionFilter, QuestionListOut)
- [ ] 创建 `backend/app/schemas/exam.py` (ExamCreate, ExamGenerateRequest, ExamOut, ExamListOut, ExamQuestionItem)
- [ ] 创建 `backend/app/schemas/submission.py` (SubmissionCreate, SubmissionOut, SubmissionListOut)

### Task 1.5: FastAPI 入口 + 路由注册

- [ ] 创建 `backend/app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import questions, exams, answers, analysis, models

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="DS Teaching Agent API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(questions.router, prefix="/api")
app.include_router(exams.router, prefix="/api")
app.include_router(answers.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(models.router, prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] 创建所有 router 占位文件 (每个至少: `from fastapi import APIRouter; router = APIRouter(tags=["name"])`)
- [ ] 启动验证: `uvicorn app.main:app --reload --port 8000` → `curl http://localhost:8000/api/health` 返回 `{"status":"ok"}`

### Task 1.6: 题库 CRUD API + Service 层

- [ ] 创建 `backend/app/services/question_service.py` (QuestionService 类: list/get/create/update/delete/batch_import)
- [ ] 实现 `backend/app/routers/questions.py`:
  - `GET /questions` — 分页+筛选
  - `GET /questions/{id}` — 单题
  - `POST /questions` — 新增
  - `PUT /questions/{id}` — 编辑
  - `DELETE /questions/{id}` — 删除
  - `POST /questions/batch-import` — JSON/Excel 批量导入
- [ ] 用 curl 测试 CRUD 全流程

### Task 1.7: 示例题库 (30 道题)

- [ ] 创建 `backend/data/sample_questions.json` (30 道，覆盖: choice×10, fill×5, tf×5, short_answer×5, code×5；知识点覆盖线性表/栈/队列/树/图/查找/排序)
- [ ] 用 Python 脚本将 JSON 转 XLSX: `python -c "..."` → `backend/data/sample_questions.xlsx`

### Task 1.8: Vue 前端骨架

- [ ] 配置 `frontend/vite.config.js` (proxy `/api` → `localhost:8000`)
- [ ] 配置 `frontend/src/main.js` (createApp + Pinia + Router)
- [ ] 配置 `frontend/src/App.vue` (NConfigProvider + NMessageProvider)
- [ ] 配置 `frontend/src/router/index.js` (13 条路由)
- [ ] 创建 `frontend/src/stores/auth.js` (role/username/userId)
- [ ] 创建 `frontend/src/api/index.js` (axios base `/api`)
- [ ] 创建所有 view 占位文件
- [ ] 验证: `npm run dev` → `http://localhost:5173`

### Task 1.9: 题库管理页面

- [ ] 创建 `frontend/src/utils/constants.js` (QUESTION_TYPES, DIFFICULTY_COLORS, KNOWLEDGE_POINTS)
- [ ] 创建 `frontend/src/api/questions.js` (getQuestions/getQuestion/createQuestion/updateQuestion/deleteQuestion/batchImportQuestions)
- [ ] 创建 `frontend/src/stores/questions.js` (Pinia store: fetchQuestions/addQuestion/editQuestion/removeQuestion/importFile)
- [ ] 创建 `frontend/src/components/KnowledgeTag.vue` (NTag 列表)
- [ ] 创建 `frontend/src/components/DifficultyStars.vue` (★☆ 显示)
- [ ] 创建 `frontend/src/components/QuestionForm.vue` (NForm: 题型/难度/知识点/题干/选项/答案/解析)
- [ ] 实现 `frontend/src/views/teacher/QuestionBank.vue`:
  - NDataTable 展示题目列表 (列: ID/题型/难度/知识点/题干/操作)
  - 筛选栏: 题型/难度/知识点下拉
  - 分页: page/pageSize
  - 新建/编辑弹窗 Modal + QuestionForm
  - 删除 NPopconfirm
- [ ] 实现 `frontend/src/views/teacher/QuestionImport.vue` (NUpload .json/.xlsx + 下载模板)

### Task 1.10: Phase 1 集成验证

- [ ] 三终端启动: `ollama serve` (可选, Phase 2 用) + `uvicorn app.main:app --reload --port 8000` + `npm run dev`
- [ ] 通过前端页面: 导入 sample_questions.json → 查看列表 → 筛选 → 编辑 → 删除 → 重新导入
- [ ] 提交: `git commit -m "chore: Phase 1 MVP complete - question bank CRUD + frontend"`

---

## Phase 2: 模型训练

### Task 2.1: 训练数据准备

- [ ] 创建 `backend/training/prepare_data.py`

脚本功能:
1. 读取 `data/sample_questions.json`
2. 转换为 Alpaca 格式 (instruction/input/output)
3. 划分 train/val (85/15)
4. 输出 `data/train.json` 和 `data/val.json`

指令模板示例:
```json
{
  "instruction": "你是一位数据结构课程出题专家。请根据以下要求生成题目。知识点：二叉树遍历，题型：选择题，难度：3",
  "input": "",
  "output": "{\"type\":\"choice\",\"difficulty\":3,...}"
}
```

- [ ] 运行: `conda activate yolo8 && cd backend && python training/prepare_data.py`
- [ ] 验证: `python -c "import json; d=json.load(open('data/train.json')); print(f'{len(d)} training samples')"`

### Task 2.2: Qwen2.5-7B QLoRA 微调

- [ ] 安装依赖: `pip install unsloth transformers datasets peft accelerate bitsandbytes`

- [ ] 创建 `backend/training/finetune_qwen.py`

核心参数:
```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
    max_seq_length=2048,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=16,
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    lora_dropout=0, bias="none",
)
# 训练: SFTTrainer, batch_size=2, grad_accum=4, lr=2e-4, 1 epoch
```

- [ ] 运行训练 (4060, ~2-4h): `conda activate yolo8 && python backend/training/finetune_qwen.py`

### Task 2.3: 导出 GGUF + Ollama 部署

- [ ] 创建 `backend/training/export_gguf.py`

```python
# 1. model.save_pretrained_merged("output/qwen-ds-teacher")
# 2. 用 llama.cpp convert 转 GGUF Q4_K_M
# 3. 创建 Ollama Modelfile
```

Modelfile:
```
FROM ./qwen-ds-teacher.Q4_K_M.gguf
TEMPLATE """{{ .System }}### Instruction: {{ .Prompt }}### Response: """
SYSTEM """你是一位数据结构课程出题和批改专家。请按JSON格式输出。"""
```

- [ ] 部署: `ollama create ds-teacher-qwen -f Modelfile`
- [ ] 验证: `ollama run ds-teacher-qwen "生成一道关于二叉树的遍历的选择题"`

### Task 2.4: BERT-tiny 小模型训练

- [ ] 创建 `backend/training/train_small.py`

两个任务:
1. **知识点多标签分类**: 输入题干 → 输出 [知识点1, 知识点2, ...]
2. **难度回归**: 输入题干 → 输出 1-5

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer
model = AutoModelForSequenceClassification.from_pretrained("prajjwal1/bert-tiny", num_labels=len(KNOWLEDGE_POINTS))
# CPU 训练, ~10min
```

- [ ] 导出 ONNX: `python -m transformers.onnx --model=output/bert-tiny-kp --feature=sequence-classification output/`
- [ ] 验证推理速度: `python -c "..."` (应该 < 50ms)

---

## Phase 3: 组卷 + 导出

### Task 3.1: 模型推理 Service

- [ ] 创建 `backend/app/services/model_service.py`

```python
import httpx, json
from ..config import settings

class ModelService:
    async def _call_ollama(self, prompt: str, system: str = "") -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "system": system, "stream": False},
                timeout=120,
            )
            return json.loads(resp.json()["response"])

    async def generate_question(self, knowledge_point: str, qtype: str, difficulty: int) -> dict:
        prompt = f"生成一道关于{knowledge_point}的{qtype}题，难度{difficulty}。返回JSON。"
        return await self._call_ollama(prompt)

    async def generate_exam(self, spec: dict) -> list[dict]:
        """spec: {knowledge_points, difficulty_distribution, type_distribution, count}"""
        # 循环调用 generate_question
        ...

    async def review_answer(self, question: dict, student_answer: str) -> dict:
        """批改主观题: {correct, score, feedback}"""
        prompt = f"题目：{question['content']}\n参考答案：{question['answer']}\n学生答案：{student_answer}\n请批改并给出评语。"
        return await self._call_ollama(prompt)
```

- [ ] 实现 `backend/app/routers/models.py`:
  - `POST /models/generate-question`
  - `POST /models/generate-exam`
  - `POST /models/review-answer`

### Task 3.2: 组卷 API + Service

- [ ] 创建 `backend/app/services/exam_service.py`

核心逻辑:
1. **规则组卷**: 根据 difficulty_distribution + type_distribution + knowledge_points 从题库随机抽取
2. **LLM 组卷**: 调用 model_service.generate_exam 生成新题
3. **混合组卷**: 部分从题库抽 + 部分 LLM 生成

```python
class ExamService:
    async def generate_exam(self, db: AsyncSession, spec: ExamGenerateRequest, model_svc: ModelService) -> Exam:
        questions = []
        # 1. 从题库按条件抽取
        for qtype, pct in spec.type_distribution.items():
            count = int(spec.question_count * pct / 100)
            # 按难度分布抽题 → query DB
            ...
        # 2. 不够的用 LLM 补
        if len(questions) < spec.question_count:
            generated = await model_svc.generate_exam(...)
            # 新题入库
            ...
        # 3. 创建 Exam + ExamQuestion
        exam = Exam(...)
        return exam
```

- [ ] 实现 `backend/app/routers/exams.py`:
  - `GET /exams` — 列表+分页
  - `POST /exams` — 手动创建
  - `GET /exams/{id}` — 详情
  - `PUT /exams/{id}` — 编辑
  - `DELETE /exams/{id}` — 删除
  - `POST /exams/{id}/generate` — 自动组卷

### Task 3.3: 试卷导出 (Word/PDF)

- [ ] 创建 `backend/app/services/export_service.py`

```python
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

class ExportService:
    def export_word(self, exam: Exam, with_answer: bool = False) -> bytes:
        doc = Document()
        doc.add_heading(exam.title, 0)
        # 按题型分组渲染
        for eq in exam.questions:
            q = eq.question
            doc.add_paragraph(f"{eq.sort_order}. [{q.type}] ({eq.score}分) {q.content}")
            if with_answer:
                doc.add_paragraph(f"答案: {q.answer}")
                doc.add_paragraph(f"解析: {q.explanation}")
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def export_pdf(self, exam: Exam, with_answer: bool = False) -> bytes:
        # 类似逻辑用 reportlab
        ...
```

- [ ] 实现导出路由: `GET /exams/{id}/export?format=pdf|word&with_answer=true|false`
- [ ] 验证: 导入示例题 → 组卷 → 导出 PDF/Word → 文件可正常打开

### Task 3.4: 试卷管理前端页面

- [ ] 创建 `frontend/src/api/exams.js`
- [ ] 创建 `frontend/src/stores/exams.js`
- [ ] 实现 `views/teacher/ExamList.vue`: 试卷列表 + 新建/删除
- [ ] 实现 `views/teacher/ExamEditor.vue`: 组卷配置表单 (难度分布滑块 + 题型配比 + 知识点选择)
- [ ] 实现 `views/teacher/ExamExport.vue`: 导出预览 + 下载按钮 (Word/PDF, 含/不含答案)

---

## Phase 4: 学生端 + 批改

### Task 4.1: 学生答题页面

- [ ] 实现 `views/student/ExamList.vue`: 可用试卷列表
- [ ] 实现 `views/student/ExamTake.vue`:
  - 倒计时 ExamTimer 组件
  - 题目逐题显示 (QuestionCard)
  - 答案输入 (选择题 radio / 填空 input / 判断 radio / 简答 textarea / 编程 textarea)
  - 提交确认

### Task 4.2: 作答提交 + 客观题批改

- [ ] 创建 `backend/app/services/grading_service.py`

```python
class GradingService:
    async def grade_submission(self, db, submission: Submission):
        exam = await db.get(Exam, submission.exam_id)
        total_score = 0
        ai_feedback = {}
        for eq in exam.questions:
            student_answer = submission.answers.get(str(eq.question_id), "")
            q = eq.question
            if q.type in ("choice", "fill", "tf"):
                correct = self._check_objective(q, student_answer)
                if correct:
                    total_score += eq.score
            else:
                # 主观题调 LLM
                result = await model_service.review_answer(q, student_answer)
                ai_feedback[str(q.id)] = result
                total_score += result.get("score", 0) * eq.score / 100
        submission.score = total_score
        submission.ai_feedback = ai_feedback
        # 错题记录
        ...
```

- [ ] 实现路由: `POST /exams/{id}/submit`, `GET /submissions/{id}`, `POST /submissions/{id}/grade`
- [ ] 创建 `frontend/src/views/student/SubmissionDetail.vue`: 答卷详情 + 分数 + AI 评语

### Task 4.3: 教师端 Dashboard

- [ ] 实现 `views/teacher/Dashboard.vue`: 题目数/试卷数/学生提交数统计卡片

### Task 4.4: 学生端 Dashboard

- [ ] 实现 `views/student/Dashboard.vue`: 待完成试卷 + 最近成绩概览

---

## Phase 5: 分析闭环

### Task 5.1: 错题本

- [ ] 创建 `backend/app/routers/analysis.py` 中的错题接口
  - `GET /analysis/student/{id}/mistakes` — 错题列表
  - `POST /analysis/student/{id}/mistakes/{qid}/mastered` — 标记掌握
- [ ] 实现 `views/student/MistakeBook.vue`: 错题列表 + 标记掌握
- [ ] 实现 `views/student/MistakePractice.vue`: 未掌握错题顺序重练

### Task 5.2: 知识点掌握度分析

- [ ] 后端: `GET /analysis/student/{id}` → 各知识点正确率热力图数据
- [ ] 前端: `components/HeatmapChart.vue` (用 Naive UI 或 ECharts)

### Task 5.3: 班级分析 (教师端)

- [ ] 后端: `GET /analysis/teacher/{id}/exams` → 班级成绩分布 + 均分趋势
- [ ] 前端: `views/teacher/Analysis.vue`

---

## Phase 6: 收尾

### Task 6.1: README + 启动脚本

- [ ] 创建 `README.md`: 项目简介 + 环境要求 + 启动步骤
- [ ] 创建 `start.sh`: 一键启动三服务

### Task 6.2: 最终集成测试

- [ ] 全流程测试: 教师导入题库 → 组卷 → 导出 → 学生答题 → 批改 → 错题重练
- [ ] 提交最终版本

---

## 任务依赖图

```
Phase 1: 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 ↘
                                                  1.8 → 1.9 → 1.10
Phase 2:                                   2.1 → 2.2 → 2.3
                                           2.1 → 2.4
                                                         ↘
Phase 3:                                     2.3 → 3.1 → 3.2 → 3.3 → 3.4
                                                                          ↘
Phase 4:                                                 1.10 → 4.1 → 4.2 → 4.3, 4.4
                                                                                ↘
Phase 5:                                                          4.2 → 5.1 → 5.2 → 5.3
                                                                                        ↘
Phase 6:                                                                         全部完成 → 6.1 → 6.2
```

Note: Phase 2 (模型训练) 可与 Phase 3-5 并行开发——后端先用 Ollama 基础 Qwen 模型做推理，微调完成后切换。
