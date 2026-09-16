# 数据结构智能出卷系统 v2 最终设计

> 2026-07-13 | 第二轮修正 | 替代 2026-07-11-ds-exam-system-v2-design.md

## 1. 概述

### 1.1 定位

纯教师端智能出卷系统。题库来自 PPT 课件的固定题目，通过 RAG 语义检索 + DeepSeek API 编排组卷，右下角集成 AI 全能对话框。

### 1.2 五条核心原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | 固定题库 | 题目来源于 PPT 提取（`ppt_extracted`）或教师手动录入（`manual`），**禁止 LLM 生成** |
| 2 | 严格范围 | 组卷结果精确匹配教师勾选的知识点/题型/难度/数量，不多不少 |
| 3 | 云端 API | 统一使用 DeepSeek API（Chat + Embedding），删除所有本地模型和训练脚本 |
| 4 | RAG 检索 | ChromaDB 向量库 + DeepSeek Embedding → 语义检索 → LLM 编排组卷 |
| 5 | AI 对话框 | 右下角浮动全能助手（组卷/查题/知识问答），传统表单与对话两种组卷方式并存 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   Vue 3 前端（纯教师端）                   │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────────┐  │
│  │ 题库管理  │ │ 知识树   │ │ 组卷    │ │ 试卷预览导出 │  │
│  └──────────┘ └──────────┘ └────────┘ └─────────────┘  │
│                    ┌──────────────────┐                  │
│                    │  AI 对话框(右下)  │                  │
│                    │  组卷/查题/问答   │                  │
│                    └──────────────────┘                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP + SSE
┌──────────────────────┴──────────────────────────────────┐
│                 FastAPI 后端                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ question │ │  exam    │ │ material │ │ knowledge │  │
│  │ router   │ │  router  │ │ router   │ │  router   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│  ┌────┴────────────┴────────────┴─────────────┴─────┐  │
│  │              RAG Pipeline                        │  │
│  │  query → DeepSeek Embedding → ChromaDB.search    │  │
│  └──────────────────────┬───────────────────────────┘  │
│  ┌──────────────────────┴───────────────────────────┐  │
│  │              LLM Adapter (DeepSeek API)           │  │
│  │  · chat (SSE流式)   · extract_questions           │  │
│  │  · assemble_exam    · parse_intent               │  │
│  └──────────────────────┬───────────────────────────┘  │
│  ┌──────────────┐ ┌─────┴─────┐ ┌──────────────────┐  │
│  │   SQLite     │ │ ChromaDB  │ │  File Parser     │  │
│  │ (题目/试卷)  │ │ (向量库)  │ │  (PPT→Markdown)  │  │
│  └──────────────┘ └───────────┘ └──────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 2.1 数据流

1. **入库流**：PPT 上传 → python-pptx 解析为 Markdown → DeepSeek API 提取题目 → 存入 SQLite → DeepSeek Embedding → 向量存入 ChromaDB
2. **组卷流**：教师需求（表单参数 / 自然语言）→ RAG 语义检索召回候选题目 → DeepSeek Chat 筛选排序 → 生成试卷预览 → DOCX 导出
3. **对话流**：用户消息 → DeepSeek Chat（带 function calling）→ 调用工具（搜题/组卷/查知识）→ SSE 流式返回结果 + 结构化卡片

---

## 3. 数据模型

### 3.1 Question（题库表）

```python
class Question(Base):
    __tablename__ = "questions"

    id: int (PK, autoincrement)
    type: str              # choice / fill / tf / short_answer / code
    difficulty: int        # 1-5
    chapter: str           # 所属章节，如"第3章 栈和队列"
    knowledge_points: list # JSON: ["栈", "后缀表达式"]
    content: str           # 题干
    options: dict | None   # 仅选择题: {"A": "...", "B": "...", "C": "...", "D": "..."}
    answer: str            # 正确答案
    explanation: str | None # 解析
    source: str            # ppt_extracted / manual（删除 llm_generated）
    material_id: int | None # FK → materials.id
    embedding_id: str | None # ChromaDB 向量 ID
    created_at: datetime
```

### 3.2 Exam / ExamQuestion（试卷表）

```python
class Exam(Base):
    __tablename__ = "exams"
    id, title, created_by, status(draft/reviewed/exported)
    total_score, duration
    requirements_json   # {"knowledge_node_ids": [...], "question_distribution": {...}, "difficulty": 3}
    knowledge_snapshot_json

class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    id, exam_id(FK), question_id(FK), score, sort_order
```

### 3.3 Material（材料表）

```python
class Material(Base):
    __tablename__ = "materials"
    id, filename, file_type(pptx/docx/pdf), file_path
    chapter, content_md, page_count, uploaded_at
```

### 3.4 KnowledgeNode（知识树）

```python
class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    id, material_id(FK), parent_id(FK→self)
    sort_order, name
    node_type(chapter/section/point)
    definition, key_terms(JSON), teaching_emphasis, source_text
```

### 3.5 ChromaDB Collection

```yaml
collection_name: "questions"
embedding_dim: 1536  # DeepSeek Embedding
metadata_fields:
  - type: str
  - difficulty: int
  - chapter: str
  - knowledge_points: str  # comma-separated
```

---

## 4. API 设计

### 4.1 材料管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/materials/upload` | 上传 PPT → 解析 → 提取题目 → 向量化 |
| POST | `/api/materials/{id}/extract` | 对已有材料重新提取题目 |
| GET | `/api/materials` | 材料列表 |

### 4.2 题库管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/questions` | 分页列表，支持 ?type=&difficulty=&chapter=&q= |
| GET | `/api/questions/search?q=二叉树遍历` | RAG 语义检索 |
| POST | `/api/questions` | 手动添加题目（自动向量化） |
| PUT | `/api/questions/{id}` | 编辑题目（自动更新向量） |
| DELETE | `/api/questions/{id}` | 删除题目（同步删 ChromaDB） |
| POST | `/api/questions/embed-all` | 全量重建向量索引 |

### 4.3 知识树

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge/nodes` | 获取完整知识树 |
| POST | `/api/knowledge/nodes` | 手动添加/调整节点 |

### 4.4 组卷 & 试卷

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/exams/generate` | 组卷（接收结构化参数） |
| GET | `/api/exams` | 试卷列表 |
| GET | `/api/exams/{id}` | 试卷详情（含题目列表） |
| PUT | `/api/exams/{id}` | 编辑试卷（替换/移除/重排题目） |
| GET | `/api/exams/{id}/export` | 导出 DOCX |

**组卷请求参数** (`POST /api/exams/generate`):

```json
{
  "title": "期中考试",
  "knowledge_node_ids": [1, 2, 5],
  "question_distribution": {
    "choice": 10,
    "fill": 5,
    "tf": 5,
    "short_answer": 3,
    "code": 2
  },
  "difficulty": 3,
  "total_score": 100,
  "duration": 120
}
```

### 4.5 AI 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | SSE 流式对话，携带 function calling 工具 |

**Function Calling 工具定义**:

| 工具名 | 触发意图 | 执行逻辑 |
|--------|---------|---------|
| `search_questions` | 查题/搜题 | ChromaDB 语义检索 → 返回题目列表卡片 |
| `generate_exam` | 组卷/出卷 | 解析 NL 参数 → RAG 召回 → LLM 编排 → 返回试卷预览卡片 |
| `query_knowledge` | 知识问答 | 查 KnowledgeNode + Material → 返回知识点卡片 |

### 4.6 删除的端点

- `POST /api/questions/generate`（LLM 生成题目）

---

## 5. 前端设计

### 5.1 整体布局

```
┌──────────────────────────────────────────────────┐
│  Header: 数据结构智能出卷系统          [教师头像]  │
├────────┬─────────────────────────────────────────┤
│        │                                         │
│ 题库管理 │         主内容区 (Router View)            │
│ 材料管理 │                                         │
│ 知识树  │    ┌──────────────────────────┐         │
│ 试卷管理 │    │                          │         │
│        │    │    当前页面的核心内容       │         │
│        │    │                          │         │
│        │    └──────────────────────────┘         │
│        │                                         │
│        │              ┌──────────────────┐       │
│        │              │  🤖 AI 助手      │       │
│        │              │                  │       │
│        │              │  [对话历史...]    │       │
│        │              │                  │       │
│        │              │  [输入框 + 发送]  │       │
│        │              └──────────────────┘       │
└────────┴─────────────────────────────────────────┘
```

### 5.2 路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 首页概览（题库统计 + 最近试卷） |
| `/questions` | QuestionBank | 题库管理（列表 + 搜索 + CRUD） |
| `/materials` | MaterialUpload | 材料上传 + 列表 |
| `/materials/:id` | MaterialDetail | 材料详情 + 提取的题目预览 |
| `/knowledge` | KnowledgeTree | 知识树浏览 + 勾选 |
| `/exams` | ExamList | 试卷列表 |
| `/exams/new` | ExamWizard | 传统表单组卷 |
| `/exams/:id` | ExamPreview | 试卷预览 + 微调 |
| `/exams/:id/export` | ExamExport | 导出确认 |

### 5.3 AI 对话框组件 `<AIChatDialog />`

**行为规格**:
- **折叠态**：右下角 56px 圆形浮动按钮，🤖 图标，绿色呼吸灯
- **展开态**：400×600px 面板，顶部标题栏可拖拽，右上角最大化/关闭
- **全屏态**：居中 900×700px 对话框面板，半透明遮罩
- **SSE 流式渲染**：AI 回复逐字显示，打字光标动画
- **快捷操作卡片**：AI 返回结构化结果时渲染为可交互卡片

**卡片类型**:

| 场景 | 卡片组件 | 交互 |
|------|---------|------|
| 搜题结果 | `QuestionCard[]` | 每题显示类型标签 + 难度星级 + 题干摘要 + "加入试卷"按钮 |
| 组卷完成 | `ExamSummaryCard` | 题型分布表 + 总分 + "预览试卷"/"导出Word"按钮 |
| 知识问答 | `KnowledgeCard` | 定义 + 关键术语 + "在知识树中查看"链接 |

**快捷入口**（对话框底部三个按钮）:
- 🎯 组卷 — 触发 generate_exam tool
- 🔍 查题 — 触发 search_questions tool
- 📖 问答 — 触发 query_knowledge tool

### 5.4 删除的内容

- App.vue 中"学生端"按钮和角色切换逻辑
- `auth.js` store 中的 role/student 相关代码
- 所有 student 路由和组件（如有残留）

---

## 6. 删除清单

| 路径 | 原因 |
|------|------|
| `backend/models/bert-*/` | 本地模型，改为 DeepSeek API |
| `backend/models/diff_checkpoints/` | 本地训练产物 |
| `backend/models/kp_checkpoints/` | 本地训练产物 |
| `backend/training/` | 训练脚本 |
| `backend/data/train.json` | 训练数据 |
| `backend/data/val.json` | 验证数据 |
| `LLMAdapter.generate_questions()` | 禁止 LLM 生成题目 |
| `Question.source = "llm_generated"` | 枚举值删除 |
| `POST /api/questions/generate` | 生成题目端点 |
| App.vue 学生端按钮 + 路由 | 纯教师端 |
| `stores/auth.js` role 切换逻辑 | 不再需要角色 |

---

## 7. 新增清单

| 路径 | 说明 |
|------|------|
| `backend/app/services/rag.py` | RAG Pipeline（embedding + ChromaDB 检索） |
| `backend/app/services/chat_service.py` | AI 对话逻辑（function calling + SSE） |
| `backend/app/routers/chat.py` | `/api/chat` SSE 端点 |
| `backend/requirements.txt` | 新增 chromadb, python-docx, openai |
| `frontend/src/components/AIChatDialog.vue` | AI 对话框组件 |
| `frontend/src/components/QuestionSearchCard.vue` | 搜题结果卡片 |
| `frontend/src/components/ExamSummaryCard.vue` | 组卷结果卡片 |
| `frontend/src/composables/useSSE.js` | SSE 流式接收 composable |

---

## 8. 错误处理

| 层级 | 场景 | 策略 |
|------|------|------|
| DeepSeek API | 超时 / 429限流 / 返回格式异常 | 重试 2 次（间隔 1s / 3s），失败返回 503 + 友好提示 |
| DeepSeek API | JSON 解析失败 | 返回原始文本 + warn 日志，不阻塞流程 |
| ChromaDB | 启动时集合不存在 | 自动调 embed-all 重建向量索引 |
| ChromaDB | 检索失败 | 降级为 SQL LIKE 模糊搜索 |
| PPT 解析 | 文件损坏 / 加密 / 格式错误 | 前端校验扩展名，后端 try-catch 返回具体错误信息 |
| 组卷 | 候选题目不足 | 返回实际可用数量和缺口，提示"建议扩大知识范围或降低题型要求" |
| 导出 | DOCX 写入失败 | 500 + "导出失败，请重试" |
| 全局 | 未捕获异常 | FastAPI exception_handler 统一返回 `{"error": "..."}` + 前端 toast |

---

## 9. 测试策略

### 9.1 后端（pytest + httpx）

```
tests/
├── test_questions.py     # CRUD / 语义检索 / embed-all
├── test_materials.py     # 上传 / PPT解析 / extract_questions
├── test_exams.py         # generate / CRUD / export
├── test_chat.py          # SSE 流式 / function calling / 卡片渲染数据
└── test_rag.py           # 检索准确性（目标: top-5 召回率 ≥ 80%）
```

### 9.2 前端（Vitest + Vue Test Utils）

```
src/__tests__/
├── AIChatDialog.spec.js   # 消息渲染 / SSE 接收 / 卡片展示 / 拖拽
├── KnowledgeTree.spec.js  # 勾选联动 / 展开折叠
└── ExamWizard.spec.js     # 参数校验 / 提交
```

---

## 10. 技术选型

| 层 | 选型 | 版本 |
|----|------|------|
| 框架 | FastAPI | ≥0.100 |
| ORM | SQLAlchemy (async) | ≥2.0 |
| 数据库 | SQLite + aiosqlite | - |
| 向量库 | ChromaDB | ≥0.4 |
| LLM | DeepSeek API (Chat + Embedding) | - |
| DOCX | python-docx | ≥1.0 |
| PPT 解析 | python-pptx | ≥0.6 |
| 前端框架 | Vue 3 + Vite | ≥3.5 / ≥8 |
| UI 库 | Naive UI | ≥2.44 |
| 状态管理 | Pinia | ≥3.0 |
| HTTP | Axios | ≥1.18 |
