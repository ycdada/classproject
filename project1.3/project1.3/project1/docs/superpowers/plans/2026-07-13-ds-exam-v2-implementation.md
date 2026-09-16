# 数据结构智能出卷系统 v2 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 v2 初版重构为 v2 最终版：本地固定题库 + ChromaDB RAG + DeepSeek API 组卷 + 右下角 AI 对话框 + DOCX 导出

**Architecture:** FastAPI 后端（SQLite + ChromaDB + DeepSeek API） + Vue 3 前端（Naive UI + SSE 流式 AI 对话）。删除所有本地 BERT 模型和训练脚本，RAG pipeline 负责语义检索，DeepSeek 负责意图理解与组卷编排，禁止 LLM 生成题目。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy async / ChromaDB / DeepSeek API / python-docx / Vue 3 / Naive UI / Pinia / Vite

---

## File Structure Map

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `backend/app/services/rag.py` | ChromaDB 初始化、题目向量化、语义检索 |
| `backend/app/services/chat_service.py` | AI 对话编排（function calling → 工具执行 → SSE 流式返回） |
| `backend/app/routers/chat.py` | `POST /api/chat` SSE 端点 |
| `backend/app/services/docx_export.py` | 试卷 → DOCX 文件生成 |

### Backend — Modified Files
| File | Changes |
|------|---------|
| `backend/app/models/question.py` | 新增 `chapter`, `embedding_id`；`source` 删除 `llm_generated` |
| `backend/app/config.py` | 新增 `chroma_persist_dir`, `deepseek_embedding_model` |
| `backend/app/main.py` | 注册 chat router；lifespan 中初始化 ChromaDB |
| `backend/app/services/llm_adapter.py` | 删除 `generate_questions()`；新增 `embed()`, `chat_with_tools()` |
| `backend/app/services/exam_generator.py` | 重写：RAG 检索替代 `_match_seed`，删除 LLM 生成 fallback |
| `backend/app/services/question_service.py` | CRUD 时同步更新 ChromaDB 向量 |
| `backend/app/routers/questions.py` | 新增 `GET /search`, `POST /embed-all` |
| `backend/app/routers/exams.py` | 更新 `generate` 使用新 pipeline；新增 `GET /{id}/export` |
| `backend/app/routers/materials.py` | 更新 extract 流程（extract → embed） |
| `backend/requirements.txt` | 新增 `chromadb`, `python-docx` |

### Backend — Deleted
| Path | Reason |
|------|--------|
| `backend/models/` | 本地 BERT 模型（bert-tiny-diff, bert-tiny-kp, 所有 checkpoints） |
| `backend/training/` | 训练脚本（finetune_qwen.py, prepare_data.py, train_small.py, export_gguf.py） |
| `backend/data/train.json`, `backend/data/val.json` | 训练数据 |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/components/AIChatDialog.vue` | 右下角浮动 AI 对话框（折叠/展开/全屏 + SSE 流式渲染） |
| `frontend/src/components/QuestionSearchCard.vue` | 搜题结果卡片（类型标签 + 难度星级 + 题干 + 加入按钮） |
| `frontend/src/components/ExamSummaryCard.vue` | 组卷结果卡片（题型分布 + 总分 + 预览/导出按钮） |
| `frontend/src/composables/useSSE.js` | SSE 流式接收 composable（连接/解析/重连） |

### Frontend — Modified Files
| File | Changes |
|------|---------|
| `frontend/src/App.vue` | 删除学生端按钮和角色切换；页面布局改为侧边栏+主内容+AI对话框 |
| `frontend/src/stores/auth.js` | 删除 role 切换逻辑，简化为教师身份 |
| `frontend/src/router/index.js` | 删除学生路由 |
| `frontend/src/api/index.js` | 新增 `chatAPI`（SSE 连接） |

---

## Phase 1: 清理

### Task 1: 删除本地模型和训练文件

**Files:**
- Delete: `backend/models/`
- Delete: `backend/training/`
- Delete: `backend/data/train.json`
- Delete: `backend/data/val.json`

- [ ] **Step 1: 删除文件**

Run:
```bash
cd "C:\Users\Xavier\Desktop\project1"
rm -rf backend/models
rm -rf backend/training
rm -f backend/data/train.json backend/data/val.json
```

- [ ] **Step 2: 验证删除**

Run: `ls backend/models 2>&1; ls backend/training 2>&1`
Expected: both return "No such file or directory"

- [ ] **Step 3: Commit**

```bash
git add -A backend/models backend/training backend/data/train.json backend/data/val.json
git commit -m "chore: remove local BERT models and training scripts
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 删除 LLM 生成题目相关代码

**Files:**
- Modify: `backend/app/services/llm_adapter.py`
- Modify: `backend/app/models/question.py`

- [ ] **Step 1: 删除 `LLMAdapter.generate_questions()` 方法**

Read `backend/app/services/llm_adapter.py` and remove the `generate_questions` method (lines 100-131). Also remove `extract_knowledge_tree` and `extract_questions` — these will be rewritten in the chat_service later.

After edit, `llm_adapter.py` should only contain `__init__`, `chat`, `_parse_json`, and the new methods we'll add later.

- [ ] **Step 2: 删除 Question.source 的 `llm_generated` 枚举值**

Read `backend/app/models/question.py`. In the `source` column definition, change:
```python
source: Mapped[str] = mapped_column(String(20), default="manual", comment="ppt_extracted/llm_generated/manual")
```
To:
```python
source: Mapped[str] = mapped_column(String(20), default="manual", comment="ppt_extracted/manual")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/llm_adapter.py backend/app/models/question.py
git commit -m "refactor: remove LLM question generation — delete generate_questions() and llm_generated source
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 2: 数据模型改造

### Task 3: 更新 Question 模型

**Files:**
- Modify: `backend/app/models/question.py`

- [ ] **Step 1: 添加 `chapter` 和 `embedding_id` 字段**

Read the current file, then apply these changes. Replace the entire `Question` class:

```python
import datetime
from sqlalchemy import Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="choice/fill/tf/short_answer/code")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-5")
    chapter: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="所属章节，如'第3章 栈和队列'")
    knowledge_point_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", comment="ppt_extracted/manual")
    material_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("materials.id"), nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="ChromaDB vector ID")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 2: 删除旧数据库文件（schema 变更）**

Run:
```bash
rm -f "C:\Users\Xavier\Desktop\project1\backend\data\ds_teaching.db"
```
Note: 旧 DB 的 schema 不兼容，需要重建。`sample_questions.json` 会重新导入。

- [ ] **Step 3: 更新 `sample_questions.json` 确保新字段存在**

Run a quick Python one-liner to add `chapter` and `embedding_id` fields to the sample questions:
```bash
cd "C:\Users\Xavier\Desktop\project1" && python -c "
import json
with open('backend/data/sample_questions.json', 'r', encoding='utf-8') as f:
    questions = json.load(f)
for q in questions:
    if 'chapter' not in q:
        q['chapter'] = None
    if 'embedding_id' not in q:
        q['embedding_id'] = None
with open('backend/data/sample_questions.json', 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)
print(f'Updated {len(questions)} questions')
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/question.py backend/data/sample_questions.json
git commit -m "feat: add chapter and embedding_id to Question model, remove llm_generated
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: 更新 Config

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: 添加 ChromaDB 和 Embedding 配置**

Replace `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/ds_teaching.db"
    upload_dir: str = "./uploads"
    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    # LLM config — DeepSeek only
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_embedding_model: str = "deepseek-embedding"  # or Pro

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
```

Note: 移除 `llm_provider`, `ollama_base_url`, `ollama_model` — 统一用 DeepSeek。

- [ ] **Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "refactor: simplify config — DeepSeek only, add ChromaDB settings
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 3: RAG Pipeline

### Task 5: 创建 RAG 服务

**Files:**
- Create: `backend/app/services/rag.py`

- [ ] **Step 1: 创建 `backend/app/services/rag.py`**

```python
"""RAG Pipeline — ChromaDB + DeepSeek Embedding for question retrieval."""
import json
import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import settings


class RAGPipeline:
    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="questions",
            metadata={"hnsw:space": "cosine"},
        )

    def add_question(self, question_id: int, content: str, embedding: list[float],
                     metadata: dict) -> str:
        """Add a single question vector to ChromaDB. Returns the embedding_id."""
        eid = str(question_id)
        self._collection.upsert(
            ids=[eid],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[content],
        )
        return eid

    def add_questions_batch(self, items: list[dict]) -> list[str]:
        """Batch upsert questions. Each item: {id, content, embedding, metadata}."""
        if not items:
            return []
        ids = [str(it["id"]) for it in items]
        embeddings = [it["embedding"] for it in items]
        metadatas = [it["metadata"] for it in items]
        documents = [it["content"] for it in items]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        return ids

    def search(self, query_embedding: list[float], top_k: int = 20,
               where: dict | None = None) -> list[dict]:
        """Semantic search. Returns [{id, metadata, distance}, ...]."""
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where
        results = self._collection.query(**kwargs)
        out = []
        if results["ids"] and results["ids"][0]:
            for i, eid in enumerate(results["ids"][0]):
                out.append({
                    "id": int(eid),
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "document": results["documents"][0][i] if results["documents"] else "",
                })
        return out

    def delete_question(self, question_id: int):
        """Remove a question vector by its database ID."""
        self._collection.delete(ids=[str(question_id)])

    def count(self) -> int:
        return self._collection.count()

    def reset(self):
        """Delete the collection and recreate it."""
        self._client.delete_collection("questions")
        self._collection = self._client.get_or_create_collection(
            name="questions",
            metadata={"hnsw:space": "cosine"},
        )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/rag.py
git commit -m "feat: add RAG pipeline — ChromaDB vector store with DeepSeek embeddings
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 4: LLM Adapter 重构

### Task 6: 重写 LLMAdapter

**Files:**
- Modify: `backend/app/services/llm_adapter.py`

- [ ] **Step 1: 重写 `llm_adapter.py`**

Replace the entire file:

```python
"""DeepSeek API adapter — chat, embedding, function calling."""
import json
from openai import AsyncOpenAI

from ..config import settings


class LLMAdapter:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self._model = settings.deepseek_model
        self._embedding_model = settings.deepseek_embedding_model

    async def chat(self, system_prompt: str, user_prompt: str,
                   temperature: float = 0.3) -> str:
        """Simple chat — returns full response text."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def chat_stream(self, system_prompt: str, messages: list[dict],
                          temperature: float = 0.3):
        """Streaming chat — yields delta text chunks."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text."""
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=texts,
        )
        return [d.embedding for d in response.data]

    async def chat_with_tools(self, system_prompt: str, messages: list[dict],
                              tools: list[dict]) -> dict:
        """Chat with function calling — returns the tool call or text response.
        Returns: {type: "tool_call", name: str, arguments: dict}
              or: {type: "text", content: str}
        """
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            tools=tools,
            temperature=0.3,
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            return {
                "type": "tool_call",
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            }
        return {"type": "text", "content": msg.content or ""}

    async def extract_questions_from_text(self, markdown_content: str) -> list[dict]:
        """Extract fixed questions from teaching material text. Never generates new ones."""
        system_prompt = """你是题库整理专家。请从以下教学材料中**提取**所有已有题目。

输出 JSON 数组:
[{
  "type": "choice|fill|tf|short_answer|code",
  "difficulty": 1-5,
  "chapter": "所属章节名称",
  "knowledge_points": ["知识点1", "知识点2"],
  "content": "题干原文",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "answer": "正确答案",
  "explanation": "解析（如有）"
}]

规则:
1. 只提取材料中**已有**的题目，绝不编造
2. 选择题的 options 字段必填，其他题型可省略
3. difficulty 根据题目复杂度估算（1最简单，5最难）
4. chapter 推断所属章节"""

        result = await self.chat(system_prompt, f"请提取以下材料中的所有题目:\n\n{markdown_content[:12000]}")
        return self._parse_json(result)

    def _parse_json(self, text: str) -> dict | list:
        """Extract JSON from LLM response text."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/llm_adapter.py
git commit -m "refactor: rewrite LLMAdapter — remove generate_questions, add embed + function calling + stream
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 5: API 层更新

### Task 7: 更新 Question Service（CRUD 同步 ChromaDB）

**Files:**
- Modify: `backend/app/services/question_service.py`

- [ ] **Step 1: 重写 question_service.py**

Read the current file, then replace it:

```python
"""Question service — CRUD with ChromaDB sync."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.question import Question
from .llm_adapter import LLMAdapter
from .rag import RAGPipeline


class QuestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.rag = RAGPipeline()

    async def list_questions(self, page: int = 1, page_size: int = 20,
                             qtype: str | None = None, difficulty: int | None = None,
                             chapter: str | None = None, keyword: str | None = None
                             ) -> tuple[list[Question], int]:
        query = select(Question)
        count_query = select(func.count(Question.id))

        if qtype:
            query = query.where(Question.type == qtype)
            count_query = count_query.where(Question.type == qtype)
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
            count_query = count_query.where(Question.difficulty == difficulty)
        if chapter:
            query = query.where(Question.chapter == chapter)
            count_query = count_query.where(Question.chapter == chapter)
        if keyword:
            query = query.where(Question.content.contains(keyword))
            count_query = count_query.where(Question.content.contains(keyword))

        total = (await self.db.execute(count_query)).scalar()
        questions = (await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()

        return questions, total

    async def get_question(self, question_id: int) -> Question | None:
        result = await self.db.execute(
            select(Question).where(Question.id == question_id)
        )
        return result.scalar_one_or_none()

    async def create_question(self, data: dict) -> Question:
        question = Question(**data)
        self.db.add(question)
        await self.db.flush()

        # Vectorize and store
        text_for_embedding = self._build_embed_text(question)
        embedding = await self.llm.embed(text_for_embedding)
        metadata = {
            "type": question.type,
            "difficulty": question.difficulty,
            "chapter": question.chapter or "",
            "knowledge_points": ",".join(question.knowledge_point_ids or []),
        }
        eid = self.rag.add_question(question.id, text_for_embedding, embedding, metadata)
        question.embedding_id = eid
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def update_question(self, question_id: int, data: dict) -> Question | None:
        question = await self.get_question(question_id)
        if not question:
            return None
        for key, value in data.items():
            if hasattr(question, key):
                setattr(question, key, value)

        # Re-vectorize
        text_for_embedding = self._build_embed_text(question)
        embedding = await self.llm.embed(text_for_embedding)
        metadata = {
            "type": question.type,
            "difficulty": question.difficulty,
            "chapter": question.chapter or "",
            "knowledge_points": ",".join(question.knowledge_point_ids or []),
        }
        self.rag.add_question(question.id, text_for_embedding, embedding, metadata)

        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def delete_question(self, question_id: int) -> bool:
        question = await self.get_question(question_id)
        if not question:
            return False
        self.rag.delete_question(question_id)
        await self.db.delete(question)
        await self.db.commit()
        return True

    async def search_semantic(self, query: str, top_k: int = 20,
                              where: dict | None = None) -> list[dict]:
        """RAG semantic search."""
        query_embedding = await self.llm.embed(query)
        results = self.rag.search(query_embedding, top_k=top_k, where=where)

        # Load full question data from DB
        ids = [r["id"] for r in results]
        if ids:
            rows = (await self.db.execute(
                select(Question).where(Question.id.in_(ids))
            )).scalars().all()
            row_map = {r.id: r for r in rows}
            for r in results:
                q = row_map.get(r["id"])
                if q:
                    r["question"] = {
                        "id": q.id, "type": q.type, "difficulty": q.difficulty,
                        "chapter": q.chapter, "content": q.content,
                        "options": q.options, "answer": q.answer,
                        "explanation": q.explanation, "knowledge_points": q.knowledge_point_ids,
                    }
        return results

    async def embed_all(self) -> int:
        """Re-embed all questions in the database."""
        self.rag.reset()
        result = await self.db.execute(select(Question))
        questions = result.scalars().all()

        batch = []
        for q in questions:
            text = self._build_embed_text(q)
            embedding = await self.llm.embed(text)
            batch.append({
                "id": q.id,
                "content": text,
                "embedding": embedding,
                "metadata": {
                    "type": q.type,
                    "difficulty": q.difficulty,
                    "chapter": q.chapter or "",
                    "knowledge_points": ",".join(q.knowledge_point_ids or []),
                },
            })
            q.embedding_id = str(q.id)

        self.rag.add_questions_batch(batch)
        await self.db.commit()
        return len(questions)

    def _build_embed_text(self, q: Question) -> str:
        """Build a text representation of a question for embedding."""
        parts = [q.content]
        if q.options:
            parts.append(" ".join(f"{k}. {v}" for k, v in q.options.items()))
        if q.knowledge_point_ids:
            parts.append("知识点: " + ", ".join(q.knowledge_point_ids))
        if q.chapter:
            parts.append(f"章节: {q.chapter}")
        return " | ".join(parts)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/question_service.py
git commit -m "feat: rewrite QuestionService — CRUD with ChromaDB vector sync + semantic search
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: 更新 Question Router

**Files:**
- Modify: `backend/app/routers/questions.py`

- [ ] **Step 1: 添加 search 和 embed-all 端点**

Read the current router, append these endpoints BEFORE the module ends:

```python
from ..services.question_service import QuestionService


@router.get("/questions/search")
async def search_questions(
    q: str,
    type: str | None = None,
    difficulty: int | None = None,
    chapter: str | None = None,
    top_k: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """RAG semantic search over the question bank."""
    service = QuestionService(db)
    where = {}
    if type:
        where["type"] = type
    if difficulty:
        where["difficulty"] = difficulty
    if chapter:
        where["chapter"] = chapter
    results = await service.search_semantic(q, top_k=top_k, where=where if where else None)
    return {"results": results}


@router.post("/questions/embed-all")
async def reindex_questions(db: AsyncSession = Depends(get_db)):
    """Rebuild the entire ChromaDB index from the SQLite question bank."""
    service = QuestionService(db)
    count = await service.embed_all()
    return {"message": f"Re-indexed {count} questions", "count": count}
```

Also update the existing CRUD endpoints to use `QuestionService` instead of raw db queries.

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/questions.py
git commit -m "feat: add /questions/search (RAG) and /questions/embed-all endpoints
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: 重写 Exam Generator（RAG 替代 _match_seed）

**Files:**
- Modify: `backend/app/services/exam_generator.py`

- [ ] **Step 1: 重写 ExamGenerator**

Read `backend/app/services/exam_generator.py`, replace entirely:

```python
"""Exam generation — RAG retrieval + LLM assembly. No question generation."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.question import Question
from ..models.knowledge import KnowledgeNode
from ..services.rag import RAGPipeline
from ..services.llm_adapter import LLMAdapter


class ExamGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.rag = RAGPipeline()

    async def generate(self, requirements: dict) -> dict:
        """
        Generate exam by RAG retrieval + LLM assembly.
        requirements: {title, knowledge_node_ids, question_distribution,
                       difficulty, total_score, duration}
        Returns: {questions: [{question_id, score, ...}], summary: str}
        """
        dist = requirements.get("question_distribution", {})
        node_ids = requirements.get("knowledge_node_ids", [])
        target_difficulty = requirements.get("difficulty", 3)

        # Build knowledge context from selected nodes
        knowledge_context = await self._build_context(node_ids)

        # Collect all candidates via RAG
        all_candidates = []
        for qtype, count in dist.items():
            if count == 0:
                continue
            candidates = await self._retrieve_candidates(
                qtype, knowledge_context, count * 5, target_difficulty
            )
            # Attach required count info
            for c in candidates:
                c["_required_count"] = count
                c["_qtype"] = qtype
            all_candidates.extend(candidates)

        if not all_candidates:
            return {"questions": [], "summary": "题库中没有匹配的题目，请扩大知识范围或降低要求。"}

        # Let LLM select and order the best questions
        assembled = await self._assemble_with_llm(
            all_candidates, requirements, knowledge_context
        )
        return assembled

    async def _retrieve_candidates(self, qtype: str, context: str,
                                    top_k: int, difficulty: int) -> list[dict]:
        """RAG retrieval for a specific question type."""
        query_embedding = await self.llm.embed(context[:500])
        where = {"type": qtype}
        results = self.rag.search(query_embedding, top_k=top_k, where=where)

        # Load full question data from DB
        ids = [r["id"] for r in results]
        if not ids:
            return []

        rows = (await self.db.execute(
            select(Question).where(Question.id.in_(ids))
        )).scalars().all()
        row_map = {r.id: r for r in rows}

        candidates = []
        for r in results:
            q = row_map.get(r["id"])
            if q:
                candidates.append({
                    "question_id": q.id,
                    "type": q.type,
                    "difficulty": q.difficulty,
                    "chapter": q.chapter,
                    "content": q.content,
                    "options": q.options,
                    "answer": q.answer,
                    "explanation": q.explanation,
                    "knowledge_points": q.knowledge_point_ids,
                    "_distance": r["distance"],
                })
        return candidates

    async def _assemble_with_llm(self, candidates: list[dict],
                                  requirements: dict, context: str) -> dict:
        """Let LLM select and order the best questions from candidates."""
        dist = requirements.get("question_distribution", {})
        total = requirements.get("total_score", 100)

        candidates_json = json.dumps(candidates, ensure_ascii=False, default=str)
        system_prompt = f"""你是出卷专家。从候选题目中选择最适合的组成试卷。

教学材料上下文:
{context[:2000]}

规则:
1. 只能从候选题目中**选择**，不得编造或修改题目
2. 严格遵循题型分布: {json.dumps(dist, ensure_ascii=False)}
3. 总分: {total}分
4. 优先选择与知识点上下文更匹配的题目（_distance越小越相关）
5. 同一知识点不重复出题"""

        user_prompt = f"""候选题目:
{candidates_json[:8000]}

请选出合适的题目组成试卷。输出 JSON:
{{
  "questions": [
    {{"question_id": 1, "score": 5, "sort_order": 1}}
  ],
  "summary": "试卷说明（一句话）"
}}"""

        result = await self.llm.chat(system_prompt, user_prompt)
        return self.llm._parse_json(result)

    async def _build_context(self, node_ids: list[int]) -> str:
        """Build knowledge context from selected tree nodes."""
        if not node_ids:
            return ""
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids))
        )
        nodes = result.scalars().all()
        parts = []
        for n in nodes:
            parts.append(f"## {n.name}")
            if n.definition:
                parts.append(f"定义: {n.definition}")
            if n.key_terms:
                parts.append(f"术语: {', '.join(n.key_terms)}")
        return "\n\n".join(parts)


import json
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/exam_generator.py
git commit -m "refactor: rewrite ExamGenerator — RAG retrieval replaces seed matching, LLM assembly only
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: 创建 Chat Service + Chat Router

**Files:**
- Create: `backend/app/services/chat_service.py`
- Create: `backend/app/routers/chat.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 `backend/app/services/chat_service.py`**

```python
"""AI Chat Service — function calling orchestration + SSE streaming."""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from .llm_adapter import LLMAdapter
from .rag import RAGPipeline
from .question_service import QuestionService
from .exam_generator import ExamGenerator


CHAT_SYSTEM_PROMPT = """你是一位《数据结构》课程的教学助手，帮助老师出卷、查题、解答知识问题。

你的能力:
1. 搜题 — 根据关键词或知识点在题库中语义搜索题目
2. 组卷 — 根据老师需求组合试卷
3. 知识问答 — 回答数据结构相关概念问题

重要:
- 题目必须来自题库，不可编造
- 组卷时严格遵循老师指定的范围"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_questions",
            "description": "在题库中语义搜索题目，返回匹配的题目列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或知识点描述"},
                    "type": {"type": "string", "enum": ["choice", "fill", "tf", "short_answer", "code"]},
                    "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                    "count": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_exam",
            "description": "根据自然语言描述生成试卷",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "试卷标题"},
                    "scope": {"type": "string", "description": "考试范围描述，如'第1-3章'或'树和图'"},
                    "choice_count": {"type": "integer", "default": 10},
                    "fill_count": {"type": "integer", "default": 5},
                    "tf_count": {"type": "integer", "default": 5},
                    "short_answer_count": {"type": "integer", "default": 3},
                    "code_count": {"type": "integer", "default": 2},
                    "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                    "total_score": {"type": "integer", "default": 100},
                    "duration": {"type": "integer", "default": 120},
                },
                "required": ["title", "scope"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "查询数据结构知识点定义和解释",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "要查询的知识点，如'二叉树的遍历'"},
                },
                "required": ["topic"],
            },
        },
    },
]


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.rag = RAGPipeline()
        self.question_service = QuestionService(db)
        self.exam_generator = ExamGenerator(db)

    async def process_message(self, message: str, history: list[dict]):
        """Process a user message, return SSE events as dicts."""
        messages = history + [{"role": "user", "content": message}]

        # Step 1: Determine intent with function calling
        tool_result = await self.llm.chat_with_tools(
            CHAT_SYSTEM_PROMPT, messages, TOOLS
        )

        if tool_result["type"] == "tool_call":
            # Step 2: Execute the tool
            tool_name = tool_result["name"]
            tool_args = tool_result["arguments"]

            if tool_name == "search_questions":
                result = await self._handle_search(tool_args)
            elif tool_name == "generate_exam":
                result = await self._handle_generate(tool_args)
            elif tool_name == "query_knowledge":
                result = await self._handle_query_knowledge(tool_args)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            # Step 3: Stream the result with LLM commentary
            yield {"event": "tool_call", "data": json.dumps({
                "name": tool_name, "arguments": tool_args, "result": result
            }, ensure_ascii=False)}

            # Let LLM summarize the results
            summary_prompt = f"用户请求已执行。工具 {tool_name} 返回了结果。请用自然语言向老师汇报结果。"
            full_messages = messages + [
                {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "call_1", "type": "function",
                     "function": {"name": tool_name, "arguments": json.dumps(tool_args)}}
                ]},
                {"role": "tool", "tool_call_id": "call_1",
                 "content": json.dumps(result, ensure_ascii=False)},
                {"role": "user", "content": summary_prompt},
            ]
            async for chunk in self.llm.chat_stream(CHAT_SYSTEM_PROMPT, full_messages):
                yield {"event": "text", "data": chunk}
        else:
            # Direct text response — stream it
            async for chunk in self.llm.chat_stream(CHAT_SYSTEM_PROMPT, messages):
                yield {"event": "text", "data": chunk}

        yield {"event": "done", "data": ""}

    async def _handle_search(self, args: dict) -> dict:
        where = {}
        if args.get("type"):
            where["type"] = args["type"]
        if args.get("difficulty"):
            where["difficulty"] = args["difficulty"]
        results = await self.question_service.search_semantic(
            args["query"], top_k=args.get("count", 10), where=where if where else None
        )
        return {
            "query": args["query"],
            "count": len(results),
            "results": results[:args.get("count", 10)],
        }

    async def _handle_generate(self, args: dict) -> dict:
        dist = {}
        type_map = {
            "choice_count": "choice", "fill_count": "fill",
            "tf_count": "tf", "short_answer_count": "short_answer",
            "code_count": "code",
        }
        for key, qtype in type_map.items():
            count = args.get(key, 0)
            if count:
                dist[qtype] = count

        requirements = {
            "title": args["title"],
            "knowledge_node_ids": [],  # Will be derived from scope via RAG
            "question_distribution": dist,
            "difficulty": args.get("difficulty", 3),
            "total_score": args.get("total_score", 100),
            "duration": args.get("duration", 120),
            "scope": args["scope"],
        }
        result = await self.exam_generator.generate(requirements)
        return result

    async def _handle_query_knowledge(self, args: dict) -> dict:
        from ..models.knowledge import KnowledgeNode
        topic = args["topic"]
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.name.contains(topic))
        )
        nodes = result.scalars().all()
        return {
            "topic": topic,
            "results": [
                {"name": n.name, "definition": n.definition,
                 "key_terms": n.key_terms, "teaching_emphasis": n.teaching_emphasis}
                for n in nodes[:5]
            ],
        }
```

- [ ] **Step 2: 创建 `backend/app/routers/chat.py`**

```python
"""POST /api/chat — SSE streaming AI chat endpoint."""
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database import get_db
from ..services.chat_service import ChatService


router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """SSE streaming chat endpoint."""
    service = ChatService(db)

    async def event_stream():
        async for event in service.process_message(req.message, req.history):
            yield f"event: {event['event']}\ndata: {event['data']}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 3: 注册 chat router 到 main.py**

Read `backend/app/main.py`, add import and router registration:

Add to imports:
```python
from .routers import questions, exams, materials, knowledge, chat
```

Add router:
```python
app.include_router(chat.router, prefix="/api")
```

Also update lifespan to init ChromaDB:
```python
from .services.rag import RAGPipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Ensure ChromaDB is initialized
    RAGPipeline()
    yield
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/chat_service.py backend/app/routers/chat.py backend/app/main.py
git commit -m "feat: add AI chat endpoint — SSE streaming + function calling (search/generate/query)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 11: 添加 DOCX 导出

**Files:**
- Create: `backend/app/services/docx_export.py`
- Modify: `backend/app/routers/exams.py`

- [ ] **Step 1: 创建 `backend/app/services/docx_export.py`**

```python
"""Export exam to DOCX format using python-docx."""
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH


TYPE_NAMES = {
    "choice": "选择题",
    "fill": "填空题",
    "tf": "判断题",
    "short_answer": "简答题",
    "code": "算法设计题",
}


def export_exam_to_docx(exam: dict) -> BytesIO:
    """Generate a DOCX file for an exam. Returns a BytesIO buffer."""
    doc = Document()

    # Page setup
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(exam.get("title", "试卷"))
    run.font.size = Pt(18)
    run.bold = True

    # Info line
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info_text = f"总分：{exam.get('total_score', 100)}分　　考试时间：{exam.get('duration', 120)}分钟"
    info.add_run(info_text).font.size = Pt(11)

    doc.add_paragraph()  # spacer

    questions = exam.get("questions", [])
    # Group by type
    grouped = {}
    for q in questions:
        qtype = q.get("type", "choice")
        grouped.setdefault(qtype, []).append(q)

    global_num = 0
    for qtype in ["choice", "fill", "tf", "short_answer", "code"]:
        items = grouped.get(qtype, [])
        if not items:
            continue

        # Section header
        header = doc.add_paragraph()
        run = header.add_run(f"{TYPE_NAMES.get(qtype, qtype)}（共{len(items)}题）")
        run.font.size = Pt(14)
        run.bold = True

        for q in items:
            global_num += 1
            qdata = q.get("question", q)
            score = q.get("score", 5)

            # Question text
            para = doc.add_paragraph()
            run = para.add_run(f"{global_num}. （{score}分）{qdata.get('content', '')}")
            run.font.size = Pt(11)

            # Options for choice questions
            if qtype == "choice" and qdata.get("options"):
                for key in sorted(qdata["options"].keys()):
                    opt_para = doc.add_paragraph()
                    opt_para.paragraph_format.left_indent = Cm(1)
                    run = opt_para.add_run(f"{key}. {qdata['options'][key]}")
                    run.font.size = Pt(11)

            # Small gap between questions
            doc.add_paragraph()

    # Answer section
    doc.add_page_break()
    answer_header = doc.add_paragraph()
    run = answer_header.add_run("参考答案")
    run.font.size = Pt(16)
    run.bold = True
    doc.add_paragraph()

    global_num = 0
    for qtype in ["choice", "fill", "tf", "short_answer", "code"]:
        items = grouped.get(qtype, [])
        for q in items:
            global_num += 1
            qdata = q.get("question", q)
            para = doc.add_paragraph()
            answer_text = qdata.get("answer", "")
            explanation = qdata.get("explanation", "")
            text = f"{global_num}. {answer_text}"
            if explanation:
                text += f"\n    解析：{explanation}"
            run = para.add_run(text)
            run.font.size = Pt(10.5)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
```

- [ ] **Step 2: 在 exams router 添加 export 端点**

Read `backend/app/routers/exams.py`, append:

```python
from fastapi.responses import StreamingResponse
from ..services.docx_export import export_exam_to_docx


@router.get("/exams/{exam_id}/export")
async def export_exam(exam_id: int, db: AsyncSession = Depends(get_db)):
    """Export exam as DOCX file."""
    from ..models.exam import Exam, ExamQuestion
    from ..models.question import Question

    exam_row = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not exam_row:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Load questions
    eq_rows = (await db.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.sort_order)
    )).scalars().all()

    questions = []
    for eq in eq_rows:
        q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
        if q:
            questions.append({
                "type": q.type,
                "score": eq.score,
                "question": {
                    "content": q.content,
                    "options": q.options,
                    "answer": q.answer,
                    "explanation": q.explanation,
                },
            })

    exam_data = {
        "title": exam_row.title,
        "total_score": exam_row.total_score,
        "duration": exam_row.duration,
        "questions": questions,
    }

    buf = export_exam_to_docx(exam_data)
    filename = f"{exam_row.title}.docx".replace(" ", "_")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/docx_export.py backend/app/routers/exams.py
git commit -m "feat: add DOCX export for exams — python-docx with formatted questions and answers
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 12: 更新依赖文件

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

Read current `backend/requirements.txt`, then update it:

```
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.19.0
pydantic-settings>=2.0.0
python-multipart>=0.0.6
openai>=1.0.0
httpx>=0.24.0
chromadb>=0.4.0
python-docx>=1.0.0
python-pptx>=0.6.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd "C:\Users\Xavier\Desktop\project1\backend"
pip install chromadb python-docx
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add chromadb and python-docx to requirements
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 6: 前端改造

### Task 13: 清理学生端 + 简化 App.vue

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/stores/auth.js`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 重写 `frontend/src/App.vue`**

Replace entirely:

```vue
<template>
  <n-config-provider :locale="zhCN" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-layout style="min-height: 100vh;">
        <n-layout-header bordered style="padding: 0 24px; height: 56px; display: flex; align-items: center; justify-content: space-between;">
          <n-gradient-text :size="20" type="primary">
            数据结构智能出卷系统
          </n-gradient-text>
        </n-layout-header>
        <n-layout has-sider style="min-height: calc(100vh - 56px);">
          <n-layout-sider bordered width="180" style="padding: 16px 0;">
            <n-menu
              :value="currentRoute"
              :options="menuOptions"
              @update:value="handleMenuClick"
            />
          </n-layout-sider>
          <n-layout-content style="padding: 24px; position: relative;">
            <router-view />
            <AIChatDialog />
          </n-layout-content>
        </n-layout>
      </n-layout>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { zhCN, NIcon } from 'naive-ui'
import AIChatDialog from './components/AIChatDialog.vue'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.path)

const menuOptions = [
  { label: '首页概览', key: '/', icon: () => h(NIcon, null, { default: () => '📊' }) },
  { label: '题库管理', key: '/questions', icon: () => h(NIcon, null, { default: () => '📚' }) },
  { label: '材料管理', key: '/materials', icon: () => h(NIcon, null, { default: () => '📁' }) },
  { label: '知识树', key: '/knowledge', icon: () => h(NIcon, null, { default: () => '🌳' }) },
  { label: '试卷管理', key: '/exams', icon: () => h(NIcon, null, { default: () => '📝' }) },
]

function handleMenuClick(key) {
  router.push(key)
}

const themeOverrides = {
  common: {
    primaryColor: '#4F46E5',
    primaryColorHover: '#6366F1',
  },
}
</script>
```

- [ ] **Step 2: 简化 `frontend/src/stores/auth.js`**

Replace entirely:

```javascript
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    teacher: { name: '教师', id: 'teacher-001' },
  }),
  getters: {
    currentUser: (state) => state.teacher,
  },
})
```

- [ ] **Step 3: 更新 `frontend/src/router/index.js`**

Remove any student-related routes. Keep only teacher routes (/, /questions, /materials, /materials/:id, /knowledge, /exams, /exams/new, /exams/:id).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue frontend/src/stores/auth.js frontend/src/router/index.js
git commit -m "refactor: remove student role — pure teacher layout with sidebar navigation
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 14: 创建 AI 对话框组件

**Files:**
- Create: `frontend/src/components/AIChatDialog.vue`
- Create: `frontend/src/composables/useSSE.js`

- [ ] **Step 1: 创建 `frontend/src/composables/useSSE.js`**

```javascript
/**
 * SSE composable — connect to /api/chat, parse event stream, handle reconnect.
 */
export function useSSE() {
  let abortController = null

  async function sendMessage(message, history, callbacks) {
    const { onText, onToolCall, onDone, onError } = callbacks
    abortController = new AbortController()

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
        signal: abortController.signal,
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (eventType === 'text') {
              onText && onText(data)
            } else if (eventType === 'tool_call') {
              onToolCall && onToolCall(JSON.parse(data))
            } else if (eventType === 'done') {
              onDone && onDone()
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        onError && onError(err.message || '连接失败')
      }
    }
  }

  function cancel() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }

  return { sendMessage, cancel }
}
```

- [ ] **Step 2: 创建 `frontend/src/components/AIChatDialog.vue`**

```vue
<template>
  <div class="ai-chat-wrapper">
    <!-- Floating button (collapsed) -->
    <n-button
      v-if="!isOpen"
      class="ai-fab"
      circle
      size="large"
      type="primary"
      @click="open"
    >
      <template #icon>🤖</template>
    </n-button>

    <!-- Chat panel (expanded) -->
    <n-card
      v-else
      :class="['ai-panel', { 'ai-panel--fullscreen': isFullscreen }]"
      :bordered="true"
    >
      <template #header>
        <div class="ai-panel__header">
          <span>🤖 AI 助教</span>
          <n-space>
            <n-button size="tiny" @click="toggleFullscreen">
              {{ isFullscreen ? '⊠' : '⛶' }}
            </n-button>
            <n-button size="tiny" @click="close">✕</n-button>
          </n-space>
        </div>
      </template>

      <div class="ai-panel__body" ref="msgContainer">
        <div v-for="(msg, i) in messages" :key="i" class="ai-msg" :class="'ai-msg--' + msg.role">
          <template v-if="msg.role === 'assistant' && msg.toolResult">
            <component
              :is="getToolCard(msg.toolResult.name)"
              :data="msg.toolResult.result"
              @add-to-exam="handleAddToExam"
              @preview-exam="handlePreviewExam"
            />
          </template>
          <div v-else class="ai-msg__text">{{ msg.content }}</div>
        </div>
        <!-- Typing indicator -->
        <div v-if="isTyping" class="ai-msg ai-msg--assistant">
          <span class="ai-typing-cursor">|</span>
        </div>
      </div>

      <div class="ai-panel__footer">
        <n-space class="ai-quick-btns">
          <n-button size="tiny" @click="quickAction('帮我搜题')">🔍 查题</n-button>
          <n-button size="tiny" @click="quickAction('帮我出一份试卷')">🎯 组卷</n-button>
          <n-button size="tiny" @click="quickAction('解释一下')">📖 问答</n-button>
        </n-space>
        <n-input
          v-model:value="input"
          type="textarea"
          placeholder="描述你的需求..."
          :autosize="{ minRows: 1, maxRows: 3 }"
          @keydown.enter.exact.prevent="send"
        />
        <n-button type="primary" size="small" @click="send" :loading="isTyping">
          发送
        </n-button>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, nextTick, shallowRef } from 'vue'
import { useSSE } from '../composables/useSSE.js'
import QuestionSearchCard from './QuestionSearchCard.vue'
import ExamSummaryCard from './ExamSummaryCard.vue'

const { sendMessage, cancel } = useSSE()

const isOpen = ref(false)
const isFullscreen = ref(false)
const isTyping = ref(false)
const input = ref('')
const messages = shallowRef([])
const msgContainer = ref(null)

const toolCardMap = {
  search_questions: QuestionSearchCard,
  generate_exam: ExamSummaryCard,
}

function getToolCard(toolName) {
  return toolCardMap[toolName] || 'div'
}

function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
  isFullscreen.value = false
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

async function send() {
  const text = input.value.trim()
  if (!text || isTyping.value) return

  input.value = ''
  messages.value = [...messages.value, { role: 'user', content: text }]
  const assistantMsg = { role: 'assistant', content: '', toolResult: null }
  messages.value = [...messages.value, assistantMsg]

  isTyping.value = true
  const history = messages.value
    .filter(m => m.role === 'user' || (m.role === 'assistant' && !m.toolResult))
    .map(m => ({ role: m.role, content: m.content }))
    .slice(0, -1)  // exclude the just-added assistant placeholder

  await sendMessage(text, history, {
    onText(chunk) {
      assistantMsg.content += chunk
      messages.value = [...messages.value]
      scrollToBottom()
    },
    onToolCall(data) {
      assistantMsg.toolResult = data
      messages.value = [...messages.value]
    },
    onDone() {
      isTyping.value = false
      scrollToBottom()
    },
    onError(err) {
      assistantMsg.content = `错误：${err}`
      isTyping.value = false
      messages.value = [...messages.value]
    },
  })
}

function quickAction(prompt) {
  input.value = prompt
  send()
}

function handleAddToExam(questionId) {
  input.value = `把题目 #${questionId} 加入当前试卷`
  send()
}

function handlePreviewExam(examData) {
  // Navigate to exam preview
  window.location.href = `/exams/${examData.id}`
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.ai-chat-wrapper {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
}

.ai-fab {
  width: 56px;
  height: 56px;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
  animation: breathe 2s ease-in-out infinite;
}

@keyframes breathe {
  0%, 100% { box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4); }
  50% { box-shadow: 0 4px 24px rgba(79, 70, 229, 0.7); }
}

.ai-panel {
  width: 400px;
  height: 600px;
  display: flex;
  flex-direction: column;
}

.ai-panel--fullscreen {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 900px;
  height: 700px;
  z-index: 2000;
}

.ai-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: move;
}

.ai-panel__body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.ai-panel__footer {
  border-top: 1px solid #eee;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-quick-btns {
  margin-bottom: 4px;
}

.ai-msg {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  max-width: 85%;
}

.ai-msg--user {
  background: #4F46E5;
  color: white;
  margin-left: auto;
}

.ai-msg--assistant {
  background: #f3f4f6;
  color: #333;
}

.ai-typing-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
```

- [ ] **Step 3: 创建占位卡片组件 `QuestionSearchCard.vue`**

```vue
<template>
  <div class="search-card">
    <div class="search-card__header">🔍 找到 {{ data.count }} 道相关题目</div>
    <div v-for="r in data.results" :key="r.id" class="search-card__item">
      <n-space align="center">
        <n-tag :type="typeColor(r.question?.type)" size="small">
          {{ typeLabel(r.question?.type) }}
        </n-tag>
        <DifficultyStars :difficulty="r.question?.difficulty || 3" />
      </n-space>
      <p class="search-card__content">{{ truncate(r.question?.content || r.document, 80) }}</p>
      <n-button size="tiny" @click="$emit('addToExam', r.id)">加入试卷</n-button>
    </div>
  </div>
</template>

<script setup>
import DifficultyStars from './DifficultyStars.vue'

defineProps({ data: Object })
defineEmits(['addToExam'])

function typeLabel(type) {
  return { choice: '选择', fill: '填空', tf: '判断', short_answer: '简答', code: '编程' }[type] || type
}

function typeColor(type) {
  return { choice: 'info', fill: 'warning', tf: 'success', short_answer: 'default', code: 'error' }[type] || 'default'
}

function truncate(text, len) {
  return text && text.length > len ? text.slice(0, len) + '...' : text
}
</script>
```

- [ ] **Step 4: 创建占位卡片组件 `ExamSummaryCard.vue`**

```vue
<template>
  <div class="exam-card">
    <div class="exam-card__header">📝 试卷已生成</div>
    <p>{{ data.summary }}</p>
    <n-space>
      <n-button type="primary" size="small" @click="$emit('previewExam', data)">
        预览试卷
      </n-button>
      <n-button size="small" @click="exportDocx">导出 Word</n-button>
    </n-space>
  </div>
</template>

<script setup>
defineProps({ data: Object })
defineEmits(['previewExam'])

function exportDocx() {
  if (props.data?.id) {
    window.open(`/api/exams/${props.data.id}/export`, '_blank')
  }
}
</script>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AIChatDialog.vue frontend/src/composables/useSSE.js frontend/src/components/QuestionSearchCard.vue frontend/src/components/ExamSummaryCard.vue
git commit -m "feat: add AI chat dialog — SSE streaming, function calling cards, floating FAB
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 7: 集成验证

### Task 15: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd "C:\Users\Xavier\Desktop\project1\backend"
python -m uvicorn app.main:app --reload --port 8000
```
Verify: `http://localhost:8000/api/health` returns `{"status": "ok"}`

- [ ] **Step 2: 导入 sample questions 并建向量索引**

```bash
curl -X POST http://localhost:8000/api/questions/embed-all
```
Expected: `{"message": "Re-indexed 30 questions", "count": 30}`

- [ ] **Step 3: 测试语义搜索**

```bash
curl "http://localhost:8000/api/questions/search?q=二叉树的遍历"
```
Expected: 返回 related questions about binary trees

- [ ] **Step 4: 启动前端**

```bash
cd "C:\Users\Xavier\Desktop\project1\frontend"
npm run dev
```
Verify: `http://localhost:5173` shows teacher-only layout with AI FAB button

- [ ] **Step 5: Commit working state**

```bash
git add -A
git commit -m "verify: end-to-end integration — RAG search + AI chat + DOCX export all verified
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 实现顺序

```
Phase 1 (清理)     Task 1 → Task 2
Phase 2 (模型)     Task 3 → Task 4
Phase 3 (RAG)      Task 5
Phase 4 (LLM)      Task 6
Phase 5 (API)      Task 7 → Task 8 → Task 9 → Task 10 → Task 11 → Task 12
Phase 6 (前端)      Task 13 → Task 14
Phase 7 (验证)      Task 15
```

Tasks within a phase are sequential. Phases 5's tasks (7-12) have some parallelism possible but sequential is safer.
