# 数据结构课程辅助教学智能体 — 设计文档

> 日期：2026-07-08 | 状态：已确认

---

## 1. 项目概述

《数据结构》课程辅助教学智能体，核心是**定制化试卷生成系统**，覆盖教师出卷 + 学生答题 + 自动批改 + 错题分析完整闭环。

### 核心目标

- 教师端：题库管理 → 智能组卷 → 导出 PDF/Word
- 学生端：在线答题 → 自动批改 → 错题重练 → 掌握度分析
- 成本优先：SQLite + 本地模型推理，零外部 API 依赖
- 功能优先：先跑通全流程，再打磨细节

---

## 2. 技术架构

```
┌─────────────────────────────────────────────────┐
│                  前端 (Vue 3)                     │
│  Naive UI  │  Vue Router  │  Pinia  │  Axios     │
│  ┌──────────────┐  ┌──────────────────────┐      │
│  │   教师工作台   │  │     学生学习端         │      │
│  │ 题库│组卷│分析 │  │ 答题│成绩│错题│复习    │      │
│  └──────────────┘  └──────────────────────┘      │
└──────────────────────┬──────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────┴──────────────────────────┐
│                后端 (FastAPI)                     │
│                                                   │
│  /api/questions    题库 CRUD + 批量导入             │
│  /api/exams        组卷 + 导出 PDF/Word             │
│  /api/answers      答题提交 + 自动批改               │
│  /api/analysis     错题分析 + 知识点掌握度            │
│  /api/models       模型推理 (题目生成/解题/批改)       │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  SQLite   │  │ ChromaDB │  │  Ollama       │    │
│  │ 结构化数据 │  │ 向量检索  │  │  本地模型推理  │    │
│  └──────────┘  └──────────┘  └──────────────┘    │
└─────────────────────────────────────────────────┘
```

### 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 前端框架 | Vue 3 + Composition API | 用户指定，生态成熟 |
| UI 组件库 | Naive UI | 开箱即用，中文友好，表格/表单/图表现成 |
| 状态管理 | Pinia | Vue 3 标准选择 |
| 后端框架 | FastAPI | 自动生成 API 文档，异步支持好 |
| ORM | SQLAlchemy + aiosqlite | 异步 SQLite 驱动 |
| 向量库 | ChromaDB (嵌入模式) | 零配置本地运行 |
| 大模型推理 | Ollama + GGUF Q4 | 4060 8G 本地推理 |
| 大模型微调 | unsloth / QLoRA | 4060 可训 7B |
| 小模型 | BERT-tiny (transformers) | CPU 训练/推理，毫秒级 |
| 试卷导出 | python-docx + reportlab | Word + PDF |

### 启动方式

```bash
# 后端
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 前端
cd frontend && npm install && npm run dev

# Ollama (模型推理服务)
ollama serve  # 预先拉取微调后的模型
```

---

## 3. 数据模型

### 3.1 题库表 (questions)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| type | VARCHAR(20) | choice / fill / tf / short_answer / code |
| difficulty | INTEGER | 1-5 |
| knowledge_points | JSON | ["二叉树遍历", "前序遍历"] |
| content | TEXT | 题干 |
| options | JSON | ["A. ...", "B. ..."] (仅选择题) |
| answer | TEXT | 正确答案 |
| explanation | TEXT | 解题思路 |
| source | VARCHAR(10) | manual / llm |
| tags | JSON | 自定义标签 |
| created_at | DATETIME | 创建时间 |

### 3.2 试卷表 (exams)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| title | VARCHAR(200) | 试卷名称 |
| created_by | VARCHAR(50) | 创建教师 ID |
| status | VARCHAR(10) | draft / ready |
| total_score | INTEGER | 总分 |
| duration | INTEGER | 考试时长(分钟) |
| created_at | DATETIME | 创建时间 |

### 3.3 试卷-题目关联表 (exam_questions)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| exam_id | INTEGER FK | 关联试卷 |
| question_id | INTEGER FK | 关联题目 |
| score | INTEGER | 本题分值 |
| sort_order | INTEGER | 排序 |

### 3.4 作答记录表 (submissions)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| student_id | VARCHAR(50) | 学生 ID |
| exam_id | INTEGER FK | 关联试卷 |
| answers | JSON | {question_id: answer, ...} |
| score | INTEGER | 得分 |
| graded_by | VARCHAR(10) | auto / teacher |
| ai_feedback | JSON | LLM 对主观题的评语 |
| submitted_at | DATETIME | 提交时间 |

### 3.5 错题本表 (mistake_records)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| student_id | VARCHAR(50) | 学生 ID |
| question_id | INTEGER FK | 错题 |
| wrong_count | INTEGER | 累计错误次数 |
| last_wrong_at | DATETIME | 最近错误时间 |
| mastered | BOOLEAN | 是否已掌握 |

---

## 4. API 设计

### 4.1 题库管理 `/api/questions`

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/questions` | 分页+筛选 (知识点/难度/题型/来源) |
| POST | `/questions` | 新增单题 |
| PUT | `/questions/{id}` | 编辑题目 |
| DELETE | `/questions/{id}` | 删除题目 |
| POST | `/questions/batch-import` | Excel/JSON 文件批量导入 |
| GET | `/questions/export` | 导出题库为 Excel |

### 4.2 模型推理 `/api/models`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/models/generate-question` | 微调模型生成单题 |
| POST | `/models/generate-exam` | 根据知识点分布自动出一整卷 |
| POST | `/models/review-answer` | 批改主观题 (简答/编程) |
| POST | `/models/analyze-knowledge` | 学生知识掌握度分析 |

### 4.3 试卷管理 `/api/exams`

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/exams` | 试卷列表 |
| POST | `/exams` | 新建试卷 |
| GET | `/exams/{id}` | 试卷详情 |
| PUT | `/exams/{id}` | 编辑试卷 |
| DELETE | `/exams/{id}` | 删除试卷 |
| POST | `/exams/{id}/generate` | 自动组卷 |
| GET | `/exams/{id}/export?format=pdf&with_answer=true` | 导出试卷 |

### 4.4 答题 `/api/answers`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/exams/{id}/submit` | 学生提交答卷 |
| GET | `/submissions/{id}` | 查看答卷详情+批改结果 |
| POST | `/submissions/{id}/grade` | 自动批改 |
| GET | `/submissions?student_id=&exam_id=` | 查询提交记录 |

### 4.5 分析 `/api/analysis`

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/analysis/student/{id}` | 知识点掌握热力图 |
| GET | `/analysis/student/{id}/mistakes` | 错题列表+重练推荐 |
| GET | `/analysis/teacher/{id}/exams` | 班级成绩分布、均分趋势 |

---

## 5. 前端路由

```
/teacher                   教师工作台首页
/teacher/questions         题库管理
/teacher/questions/import  批量导入
/teacher/exams             试卷管理
/teacher/exams/create      新建/编辑试卷
/teacher/exams/:id/export  导出预览
/teacher/analysis          班级分析

/student                   学生端首页
/student/exams             我的试卷列表
/student/exams/:id         开始答题
/student/submissions/:id   查看批改结果
/student/mistakes          我的错题本
/student/mistakes/practice 错题重练
```

---

## 6. 模型训练方案

### 6.1 模型分工

| | 模型 A（大模型） | 模型 B（小模型） |
|---|---|---|
| **任务** | 题目生成、解题过程解析、主观题批改 | 知识点自动标注、难度预测、题目查重 |
| **基座** | Qwen2.5-7B-Instruct | BERT-tiny (~4M params) |
| **方法** | QLoRA (4-bit + LoRA) | 全参数训练 |
| **硬件** | RTX 4060 8G | CPU |
| **训练时间** | ~2-4 小时 | ~10 分钟 |
| **推理** | Ollama + GGUF Q4_K_M | Transformers ONNX |
| **推理显存** | ~4.5 GB | 0 (CPU) |

### 6.2 数据集准备

目标：精心整理 500-2000 道数据结构题目。

```json
{
  "type": "choice",
  "difficulty": 3,
  "knowledge_points": ["二叉树遍历", "前序遍历", "递归"],
  "content": "已知二叉树的前序遍历序列为 ABCDEF，中序遍历序列为 CBDAEF，则该二叉树的后序遍历序列为？",
  "options": ["A. CDBFEA", "B. CDBAFE", "C. CBDFEA", "D. CDBEFA"],
  "answer": "A",
  "explanation": "前序：根左右 → A为根。中序：左根右 → CBD为左子树，EF为右子树。递归构建得后序：CDBFEA。"
}
```

### 6.3 训练流程

```
1. 数据预处理
   - 收集整理题目 JSON → 转换 Alpaca 格式
   - 指令模板化："根据[知识点]，生成一道[题型]，难度[1-5]"
   - 划分 train/val (85/15)

2. 大模型微调 (4060)
   - 框架: unsloth + transformers
   - 方法: QLoRA (load_in_4bit=True)
   - LoRA rank=16, alpha=16
   - batch_size=2, gradient_accumulation=4
   - 1 epoch, learning_rate=2e-4
   - 导出: GGUF Q4_K_M → Ollama Modelfile

3. 小模型训练 (CPU)
   - 任务1: 知识点多标签分类
   - 任务2: 难度回归/分类
   - 框架: transformers Trainer
   - 导出: ONNX → onnxruntime
```

### 6.4 训练数据示例模板（Alpaca 格式）

```json
{
  "instruction": "你是一位数据结构课程出题专家。请生成一道关于二叉树遍历的选择题，难度为3。",
  "input": "",
  "output": "{\n  \"content\": \"已知二叉树的前序遍历序列为ABCDEF...\",\n  \"options\": [\"A. CDBFEA\", ...],\n  \"answer\": \"A\",\n  \"explanation\": \"前序根左右...\",\n  \"difficulty\": 3,\n  \"knowledge_points\": [\"二叉树遍历\", \"前序遍历\"]\n}"
}
```

---

## 7. 项目目录结构

```
ds-teaching-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app 入口
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # SQLite 连接 + 建表
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── question.py
│   │   │   ├── exam.py
│   │   │   ├── submission.py
│   │   │   └── mistake.py
│   │   ├── schemas/             # Pydantic 验证
│   │   │   ├── __init__.py
│   │   │   ├── question.py
│   │   │   ├── exam.py
│   │   │   └── submission.py
│   │   ├── routers/             # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── questions.py
│   │   │   ├── exams.py
│   │   │   ├── answers.py
│   │   │   ├── analysis.py
│   │   │   └── models.py
│   │   ├── services/            # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── question_service.py
│   │   │   ├── exam_service.py
│   │   │   ├── grading_service.py
│   │   │   ├── export_service.py
│   │   │   └── model_service.py  # Ollama 推理客户端
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── embedding.py     # ChromaDB 向量化
│   ├── data/                    # SQLite DB + 示例题库
│   │   ├── sample_questions.json
│   │   └── sample_questions.xlsx
│   ├── models/                  # 微调后的模型文件 (gitignored)
│   │   └── ollama_modelfile
│   ├── training/                # 训练脚本
│   │   ├── prepare_data.py
│   │   ├── finetune_qwen.py     # 大模型 QLoRA 微调
│   │   ├── train_small.py       # 小模型训练
│   │   └── export_gguf.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── stores/              # Pinia stores
│   │   │   ├── auth.js
│   │   │   ├── questions.js
│   │   │   ├── exams.js
│   │   │   └── submissions.js
│   │   ├── views/
│   │   │   ├── teacher/
│   │   │   │   ├── Dashboard.vue
│   │   │   │   ├── QuestionBank.vue
│   │   │   │   ├── QuestionImport.vue
│   │   │   │   ├── ExamList.vue
│   │   │   │   ├── ExamEditor.vue
│   │   │   │   ├── ExamExport.vue
│   │   │   │   └── Analysis.vue
│   │   │   └── student/
│   │   │       ├── Dashboard.vue
│   │   │       ├── ExamList.vue
│   │   │       ├── ExamTake.vue
│   │   │       ├── SubmissionDetail.vue
│   │   │       ├── MistakeBook.vue
│   │   │       └── MistakePractice.vue
│   │   ├── components/          # 共享组件
│   │   │   ├── QuestionCard.vue
│   │   │   ├── QuestionForm.vue
│   │   │   ├── KnowledgeTag.vue
│   │   │   ├── DifficultyStars.vue
│   │   │   ├── HeatmapChart.vue
│   │   │   └── ExamTimer.vue
│   │   ├── api/                 # Axios 封装
│   │   │   ├── index.js
│   │   │   ├── questions.js
│   │   │   ├── exams.js
│   │   │   ├── answers.js
│   │   │   └── analysis.js
│   │   └── utils/
│   │       └── constants.js     # 知识点列表、题型映射
│   ├── package.json
│   └── vite.config.js
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-07-08-ds-teaching-agent-design.md
└── README.md
```

---

## 8. 开发顺序

### 阶段一：基础设施 + 题库管理 (MVP 核心)

1. FastAPI 项目骨架 + SQLite 建表
2. 题库 CRUD API
3. 批量导入 (JSON + Excel 示例文件)
4. Vue 前端骨架 + 路由 + 题库管理页面
5. 示例题库文件 (30-50 道，覆盖各知识点和题型)

### 阶段二：模型训练

6. 整理 500+ 道训练数据
7. Qwen2.5-7B QLoRA 微调
8. BERT-tiny 小模型训练 (知识点标注 + 难度预测)
9. Ollama 部署 + FastAPI 模型推理接口

### 阶段三：组卷 + 导出

10. 智能组卷 API (知识点覆盖 + 难度分布 + 题型配比)
11. 试卷 CRUD + 前端试卷管理页面
12. Word/PDF 导出 (含答案版/无答案版)

### 阶段四：学生端 + 批改

13. 学生端路由 + 答题页面
14. 作答提交 + 客观题自动批改
15. 主观题 LLM 批改 + AI 评语
16. 成绩查看页面

### 阶段五：分析闭环

17. 错题本 + 重练模式
18. 知识点掌握度热力图
19. 班级成绩分析 (教师端)

---

## 9. 部署方案 (演示环境)

```bash
# 终端1: Ollama 模型推理
ollama serve

# 终端2: FastAPI 后端
cd backend
cp .env.example .env   # 编辑数据库路径等
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 终端3: Vue 前端
cd frontend
npm install
npm run dev   # http://localhost:5173
```

3 个终端、无 Docker、无外部 API 依赖，纯本地运行。

---

## 10. 非功能需求

### 性能
- 题库查询 (带筛选): < 200ms
- 组卷 (< 50 题): < 2s (规则匹配)
- 模型生成单题: < 30s (4060 CPU 推理) / < 5s (GPU 推理)
- 试卷导出: < 5s

### 安全 (本地演示，最低要求)
- 教师/学生通过简单用户名区分，不做复杂鉴权
- 数据库本地文件，无需加密

### 可扩展
- LLM 客户端通过 config 切换，支持后期接入外部 API
- SQLite → PostgreSQL 迁移路径 (SQLAlchemy 抽象层)

---

## 11. 自检清单

- [x] 无 TBD / TODO 占位符
- [x] API 设计与数据模型一致
- [x] 前端路由覆盖所有 API 功能
- [x] 模型训练方案适配 4060 硬件
- [x] 开发顺序合理，每阶段可独立验证
- [x] 无外部 API 依赖，纯本地可运行
