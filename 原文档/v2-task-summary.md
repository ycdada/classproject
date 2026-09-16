# 数据结构智能出卷系统 v2 — 15 Tasks 修改总结

> 从 v1 教学助手重构为 v2 纯教师端智能出卷系统。架构从「本地模型推理 + 学生端」转为「固定题库 + RAG 语义检索 + DeepSeek API 对话 + AI 对话框前端」。

---

## 架构对比

| 维度 | v1 | v2 |
|---|---|---|
| 定位 | 教师 + 学生双端 | 纯教师端 |
| 模型 | Ollama Qwen + BERT-tiny 本地推理 | DeepSeek API（对话）+ 本地 SentenceTransformer（嵌入） |
| 出卷 | LLM 逐题生成 | 固定题库 + RAG 语义检索 |
| 学生端 | 答题 / 批改 / 错题本 | **已删除** |
| 新增 | — | 材料上传解析 / 知识树提取 / AI 对话 / DOCX 导出 |
| 存储 | SQLite | SQLite + ChromaDB 向量库 |

---

## Task 1: 清理 v1 学生端代码

**Commit:** `b0717c9` / `6054ad1` / `5d11d05`

### 删除的后端文件
| 文件 | 说明 |
|---|---|
| `models/submission.py` | 学生提交记录模型 |
| `models/mistake.py` | 错题记录模型 |
| `routers/answers.py` | 学生答题路由 |
| `routers/analysis.py` | 分析路由 |
| `routers/models.py` | 模型推理路由 |
| `services/grading_service.py` | 自动批改服务 |
| `services/model_service.py` | Ollama 模型推理服务 |
| `schemas/submission.py` | 提交 Schema |
| `utils/embedding.py` | 旧嵌入工具 |

### 删除的前端文件
| 文件 | 说明 |
|---|---|
| `views/student/` (整个目录) | 学生端所有页面 |
| `views/teacher/QuestionImport.vue` | 旧导入页 |
| `views/teacher/Analysis.vue` | 旧分析页 |
| `components/HeatmapChart.vue` | 热力图 |
| `components/ExamTimer.vue` | 考试倒计时 |
| `api/answers.js` / `api/analysis.js` | 旧 API 客户端 |
| `stores/submissions.js` | 提交状态管理 |

### 修改
- `main.py` — 移除 v1 routers（answers/analysis/models），新增 v2 routers（materials/knowledge/chat）
- `router/index.js` — 移除 student 路由，新增 v2 路由

---

## Task 2: 重构数据模型

**Commit:** `3a0e789` / `4b52885` / `69ec182`

### Question 模型变更
```python
# 新增字段
chapter: str | None          # 所属章节（如"第3章 栈和队列"）
embedding_id: str | None     # ChromaDB 向量 ID
source: str                  # 来源：ppt_extracted / manual
material_id: int | None      # 关联材料 FK

# 删除字段
llm_generated                # 不再标注 LLM 来源
tags                         # 简化为 knowledge_point_ids

# 修改字段
knowledge_points → knowledge_point_ids  # 重命名
```

### Exam 模型变更
```python
# 新增字段
requirements_json: dict | None        # 组卷需求快照
knowledge_snapshot_json: dict | None  # 知识点快照

# 保留
ExamQuestion 关联表（exam_id + question_id + score + sort_order）
```

### 新增模型

**Material（材料表）**
| 字段 | 类型 | 说明 |
|---|---|---|
| id | int | 主键 |
| filename | str | 原始文件名 |
| file_type | str | pptx/docx/pdf/md |
| file_path | str | 服务器存储路径 |
| chapter | int? | 章节号 |
| content_md | str? | 解析后的 Markdown |
| page_count | int | 页数 |
| uploaded_at | datetime | 上传时间 |

**KnowledgeNode（知识树节点）**
| 字段 | 类型 | 说明 |
|---|---|---|
| id | int | 主键 |
| material_id | int | FK → materials |
| parent_id | int? | FK → 父节点（自引用树） |
| sort_order | int | 排序 |
| name | str | 节点名称 |
| node_type | str | chapter/section/point |
| definition | str? | 定义原文 |
| key_terms | list? | 关键术语 |
| teaching_emphasis | str? | 教学重点 |

---

## Task 3: 简化配置（DeepSeek 单一 LLM）

**Commit:** `8764090`

### `config.py` 简化
```python
# v1: ollama + chroma + embedding_model
# v2: 只保留 DeepSeek + ChromaDB
class Settings(BaseSettings):
    database_url: str
    upload_dir: str
    chroma_persist_dir: str
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    local_embedding_model: str = "BAAI/bge-small-zh-v1.5"  # ← Task 15 修复
```

**移除的配置:** `llm_provider`, `ollama_base_url`, `ollama_model`

---

## Task 4: 文件解析服务

**Commit:** `d8d9514`

### `services/file_parser.py`

统一解析器，输入文件路径 + 类型 → 输出 Markdown 文本 + 页数：

| 格式 | 解析方式 | 输出 |
|---|---|---|
| `.pptx` | python-pptx 提取 shape 文本 + 表格 | Slide 标题 + 文本 |
| `.docx` | python-docx 提取段落 + 保留标题层级 | Markdown heading |
| `.pdf` | PyMuPDF (fitz) 逐页提取 | 页分隔 |
| `.md` | 直接读取 | 原文 |

**依赖新增:** `python-pptx`, `PyMuPDF`

---

## Task 5: LLM 适配器（DeepSeek API）

**Commit:** `d8d9514` + Task 15 修复

### `services/llm_adapter.py`

```python
class LLMAdapter:
    # Chat — DeepSeek API
    async def chat(system_prompt, user_prompt, temperature) -> str
    async def chat_stream(system_prompt, messages, temperature)  # SSE 流式
    async def chat_with_tools(system_prompt, messages, tools)     # Function Calling

    # Embedding — 本地 SentenceTransformer（Task 15 修复）
    async def embed(text) -> list[float]
    async def embed_batch(texts) -> list[list[float]]

    # 题目提取
    async def extract_questions_from_text(markdown_content) -> list[dict]
```

**关键设计:**
- DeepSeek 对话用 OpenAI SDK（`openai.AsyncOpenAI`）
- DeepSeek **没有** embedding API → 改用本地 `BAAI/bge-small-zh-v1.5` 模型
- Embedding 同步 encode 通过 `asyncio.to_thread()` 包装，避免阻塞
- `local_files_only=True` 优先从缓存加载

**依赖新增:** `openai>=1.0.0`, `sentence-transformers>=3.0.0`

---

## Task 6: RAG 流水线（ChromaDB 向量库）

**Commit:** `4b52885` / `72ff4d7`

### `services/rag.py`

```python
class RAGPipeline:
    def add_question(question_id, content, embedding, metadata)  # 单条入库
    def add_questions_batch(items)                                 # 批量入库
    def search(query_embedding, top_k, where)                      # 余弦相似度检索
    def delete_question(question_id)                               # 删除向量
    def reset()                                                    # 重建集合
```

**ChromaDB 配置:**
- 持久化目录: `./data/chroma`
- 距离度量: `cosine`
- 集合名: `questions`

---

## Task 7: Pydantic Schemas

**Commit:** `e3858ba` + `392295e`

### 新增 Schemas
| 文件 | 内容 |
|---|---|
| `schemas/material.py` | `MaterialOut`, `MaterialListItem` |
| `schemas/knowledge.py` | `KnowledgeNodeOut`, `KnowledgeNodeUpdate` |

### 修改 Schemas
| 文件 | 变更 |
|---|---|
| `schemas/question.py` | `QuestionCreate` 新增 chapter/source/material_id；`QuestionUpdate` 新增 chapter；`QuestionOut` 新增 chapter/embedding_id |
| `schemas/exam.py` | 新增 `ExamRequirements`（题型配比 + 难度分布 + 知识点选择 + 重点方向） |

### Bug Fix
- `392295e`: 示例题 options 改为 dict 格式（`{"A": "..."}` 而非 `["A. ..."]`）
- `392295e`: `list_questions` 路由签名修复（参数名 `type`/`difficulty`/`chapter`/`keyword`）

---

## Task 8: Materials API 路由

**Commit:** `e3858ba`

### `routers/materials.py`
| 端点 | 说明 |
|---|---|
| `POST /api/materials/upload` | 上传文件 → 解析 → 入库 |
| `GET /api/materials` | 材料列表 |
| `GET /api/materials/{id}` | 材料详情（含解析内容） |
| `DELETE /api/materials/{id}` | 删除材料 + 物理文件 |

---

## Task 9: Knowledge Tree API 路由

**Commit:** `e3858ba`

### `routers/knowledge.py`
| 端点 | 说明 |
|---|---|
| `POST /api/knowledge/extract/{material_id}` | LLM 提取章→节→点三层知识树 |
| `GET /api/knowledge/tree/{material_id}` | 获取嵌套树结构 |
| `PUT /api/knowledge/nodes/{node_id}` | 教师手动修正节点 |
| `DELETE /api/knowledge/tree/{material_id}` | 删除知识树 |

**知识树提取 Prompt:**
- 从材料 Markdown 中提取章节→知识点三层结构
- 每条知识点保留：定义原文、关键术语、教学重点
- 不自行发挥，只提取材料中明确讲授的内容

---

## Task 10: Question Service（含 RAG 同步）

**Commit:** `72ff4d7`

### `services/question_service.py`

```python
class QuestionService:
    # CRUD
    async def list_questions(page, page_size, filters)    # 分页 + 筛选
    async def get_question(question_id)
    async def create_question(data)                        # 自动向量化 + ChromaDB
    async def update_question(question_id, data)            # 重新向量化
    async def delete_question(question_id)                  # 级联删除向量

    # RAG
    async def search_semantic(query, top_k, where)          # 语义检索

    # 工具
    async def embed_all()                                   # 全库重建索引
```

**关键逻辑:** 创建/更新题目时自动调用 `llm.embed()` 生成向量 → `rag.add_question()` 存入 ChromaDB。

### `routers/questions.py` 新增端点
| 端点 | 说明 |
|---|---|
| `GET /api/questions/search?q=...` | RAG 语义搜索（**必须**在 `/{id}` 之前注册） |
| `POST /api/questions/embed-all` | 全库重建 ChromaDB 索引 |
| `POST /api/questions/extract/{material_id}` | LLM 从材料提取题目 |

---

## Task 11: 考试生成 + 导出

**Commit:** `ab2bbd2` / `72ff4d7`

### `services/exam_generator.py`
```python
class ExamGenerator:
    async def generate(requirements) -> list[dict]
    # 1. 从知识树节点构建上下文
    # 2. 优先从种子题库匹配
    # 3. 不够时 LLM 补充
```

### `services/export_service.py` + `services/docx_export.py`
- `python-docx` 生成 Word 文档
- 试卷结构：标题 → 信息栏 → 按题型分组渲染 → 分数线
- 支持含答案/不含答案两种版本

### `routers/exams.py`
| 端点 | 说明 |
|---|---|
| `POST /api/exams/generate` | 提交组卷需求 → 生成试卷 |
| `GET /api/exams` | 试卷列表 |
| `GET /api/exams/{id}` | 试卷详情（含题目） |
| `PUT /api/exams/{id}/questions/{eq_id}` | 替换/编辑题目 |
| `GET /api/exams/{id}/export` | 导出 DOCX |
| `DELETE /api/exams/{id}` | 删除试卷 |

---

## Task 12: AI Chat API

**Commit:** `72ff4d7`

### `services/chat_service.py`
- 使用 `llm.chat_stream()` 流式对话
- 系统提示词定位为"数据结构教学助手"
- 支持多轮对话历史

### `routers/chat.py`
| 端点 | 说明 |
|---|---|
| `POST /api/chat/send` | 发送消息 → SSE 流式返回 |

---

## Task 13: 前端 API 客户端

**Commit:** `69ee299` / `098dce1`

### 新增 / 修改
| 文件 | 说明 |
|---|---|
| `api/materials.js` | `upload` / `list` / `get` / `delete` |
| `api/knowledge.js` | `extract` / `getTree` / `updateNode` / `deleteTree` |
| `api/exams.js` | `generate` / `list` / `get` / `replaceQuestion` / `exportExam` / `delete` |
| `api/questions.js` | 新增 `search` / `extract` / `embedAll` |
| `composables/useSSE.js` | SSE 流式接收工具 |

---

## Task 14: 前端页面

**Commit:** `69ee299` / `098dce1` / `392295e`

### 全部页面（纯教师端）
| 页面 | 路由 | 说明 |
|---|---|---|
| Dashboard | `/dashboard` | 材料 + 试卷概览、快捷入口 |
| QuestionBank | `/questions` | 题库管理（CRUD + 筛选 + 语义搜索） |
| MaterialUpload | `/materials/upload` | 上传材料 + 自动解析 |
| MaterialDetail | `/materials/:id` | 解析内容预览 |
| KnowledgeTree | `/knowledge/:materialId` | LLM 提取知识树 + 节点勾选组卷 |
| ExamList | `/exams` | 试卷列表 |
| ExamWizard | `/exams/create` | 组卷向导（题型配比 + 难度分布表单） |
| ExamPreview | `/exams/:id` | 试卷预览 + 答案展开 + DOCX 导出 |

### 组件
| 组件 | 说明 |
|---|---|
| `AIChatDialog.vue` | 右下角 FAB 浮动按钮 → 侧边栏 AI 对话面板 |
| `KnowledgeTreePanel.vue` | NTree 递归渲染知识树（可勾选） |
| `QuestionCard.vue` / `QuestionForm.vue` | 题目展示 / 编辑表单 |
| `KnowledgeTag.vue` / `DifficultyStars.vue` | 知识点标签 / 难度星级 |
| `QuestionSearchCard.vue` / `ExamSummaryCard.vue` | 搜索结果卡片 / 试卷摘要 |

### 布局
- 左侧固定导航栏（📊 首页 / 📚 题库 / 📁 材料 / 🌳 知识树 / 📝 试卷）
- 右下角浮动 AI 助手按钮 → 点击展开右侧聊天面板

---

## Task 15: 嵌入 API 修复（本次完成）

**未提交（本次会话修复）**

### 问题
DeepSeek API **不提供** embedding 端点（`deepseek-embedding` 模型返回 404）。

### 修复（4 个文件）
| 文件 | 变更 |
|---|---|
| `config.py` | `deepseek_embedding_model` → `local_embedding_model`；添加 HF mirror 环境变量 |
| `llm_adapter.py` | `embed()` / `embed_batch()` 改用本地 `SentenceTransformer` + `asyncio.to_thread()` |
| `.env` | `LOCAL_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5` |
| `.env.example` | 同步更新 |
| `requirements.txt` | 新增 `sentence-transformers>=3.0.0` |

### 技术方案
- **模型:** `BAAI/bge-small-zh-v1.5`（24MB, 512维, 中文优化）
- **加载:** `local_files_only=True` 优先缓存加载（首次需 `HF_ENDPOINT=hf-mirror.com`）
- **线程安全:** `asyncio.to_thread()` 将同步 encode 包装为异步

---

## 完整文件变更清单

### 后端 (backend/app/)

```
models/
  ✕ submission.py, mistake.py          — 删除
  ~ question.py                         — 新增 chapter, embedding_id, source, material_id
  ~ exam.py                             — 新增 requirements_json, knowledge_snapshot_json
  + material.py                         — 新建
  + knowledge.py                        — 新建

routers/
  ✕ answers.py, analysis.py, models.py — 删除
  ~ questions.py                        — 新增 search, embed-all, extract 端点
  ~ exams.py                            — 重写为 generate 流水线
  + materials.py                        — 新建
  + knowledge.py                        — 新建
  + chat.py                             — 新建

services/
  ✕ grading_service.py, model_service.py — 删除
  ~ question_service.py                  — 新增 RAG 同步逻辑
  ~ exam_service.py                      — 保留（简单规则筛选）
  ~ export_service.py                    — 保留 + 新增 docx_export.py
  + llm_adapter.py                       — 新建（DeepSeek 对话 + 本地嵌入）
  + rag.py                               — 新建（ChromaDB 向量库）
  + file_parser.py                       — 新建（多格式解析器）
  + exam_generator.py                    — 新建（组卷流水线）
  + chat_service.py                      — 新建（AI 对话）

schemas/
  ✕ submission.py                        — 删除
  ~ question.py, exam.py                 — 新增 v2 字段
  + material.py, knowledge.py            — 新建

utils/
  ✕ embedding.py                         — 删除

config.py                                — 简化为 DeepSeek only + 本地嵌入
main.py                                  — 更新路由注册 + ChromaDB 初始化
```

### 前端 (frontend/src/)

```
views/student/                   — 整个目录删除
  ✕ ExamList.vue, ExamTake.vue, Dashboard.vue,
    SubmissionDetail.vue, MistakeBook.vue, MistakePractice.vue

views/teacher/
  ✕ QuestionImport.vue, Analysis.vue — 删除
  ~ Dashboard.vue                     — 重写为材料+试卷中心
  ~ QuestionBank.vue                  — 新增语义搜索
  ~ ExamList.vue                      — 更新
  ✕ ExamEditor.vue                    — 替换为 ExamWizard
  ✕ ExamExport.vue                    — 替换为 ExamPreview
  + MaterialUpload.vue                — 新建
  + MaterialDetail.vue                — 新建
  + KnowledgeTree.vue                 — 新建
  + ExamWizard.vue                    — 新建
  + ExamPreview.vue                   — 新建

components/
  ✕ HeatmapChart.vue, ExamTimer.vue   — 删除
  ~ QuestionCard.vue, QuestionForm.vue — 保持
  + KnowledgeTreePanel.vue            — 新建
  + AIChatDialog.vue                  — 新建（SSE 流式 + FAB）
  + QuestionSearchCard.vue            — 新建
  + ExamSummaryCard.vue               — 新建

api/
  ✕ answers.js, analysis.js           — 删除
  + materials.js, knowledge.js        — 新建
  ~ exams.js, questions.js            — 更新

stores/
  ✕ submissions.js                    — 删除

composables/
  + useSSE.js                         — 新建

router/index.js                       — 删除 student 路由，新增 v2 路由
App.vue                               — 添加侧边栏 + AI 对话框
```

---

## Git 提交历史

| 提交 | 说明 | 对应 Task |
|---|---|---|
| `23de459` | v2 设计文档 | — |
| `b66e7c1` | v2 实现计划（15 tasks） | — |
| `b0717c9` | 删除 v1 学生端代码 | Task 1 |
| `6054ad1` | 删除本地 BERT 模型和训练脚本 | Task 1 |
| `5d11d05` | 删除 LLM 题目生成 | Task 1 |
| `69ec182` | 更新 Question/Exam 模型，新增 Material/KnowledgeNode | Task 2 |
| `d8d9514` | 文件解析器 + LLM 适配器 | Task 4, 5 |
| `e3858ba` | Schemas + Materials/KNOWLEDGE 路由 | Task 6, 7, 8, 9 |
| `ab2bbd2` | 考试生成流水线 | Task 10, 11 |
| `69ee299` | 前端全部页面 + API 客户端 | Task 13, 14 |
| `8764090` | 简化配置：DeepSeek only + ChromaDB | Task 3 |
| `3a0e789` | Question 模型新增 chapter/embedding_id | Task 2 |
| `4b52885` | RAG 流水线集成 | Task 6 |
| `72ff4d7` | 后端 v2 重构完成：RAG + AI Chat + DOCX 导出 | Task 10, 11, 12 |
| `098dce1` | AI Chat 前端：SSE 流式 + FAB 浮动按钮 | Task 14 |
| `392295e` | Bug Fix: options dict 格式 + list_questions 签名 | Task 7 |
| **未提交** | 嵌入 API 修复（本地 SentenceTransformer） | **Task 15** |

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | SQLite (aiosqlite, 异步) |
| 向量库 | ChromaDB (PersistentClient, cosine) |
| LLM 对话 | DeepSeek API (deepseek-chat, OpenAI SDK) |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 (SentenceTransformer, 本地) |
| 文件解析 | python-pptx + python-docx + PyMuPDF |
| 文档导出 | python-docx |
| 前端框架 | Vue 3 + Vite |
| UI 库 | Naive UI |
| 状态管理 | Pinia |
| HTTP 客户端 | Axios |
| AI 对话 | SSE (Server-Sent Events) 流式 |

---

## 待提交

```bash
git add backend/app/config.py backend/app/services/llm_adapter.py \
        backend/.env backend/.env.example backend/requirements.txt
git commit -m "fix: replace DeepSeek embedding with local SentenceTransformer (BGE-small-zh)

DeepSeek does not provide an embedding API (returns 404).
Switched to BAAI/bge-small-zh-v1.5 loaded via sentence-transformers
with local_files_only=True and asyncio.to_thread() for non-blocking.
Added HF mirror config for first-time model download.

Co-Authored-By: Claude <noreply@anthropic.com>"
```
