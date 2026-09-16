# 数据结构智能出卷系统 v2 — 设计文档

> 日期：2026-07-11 | 状态：待确认

---

## 1. 项目定位

纯教师端智能出卷系统。核心价值：**试卷术语定义和解题思路严格对齐教师自己的教案**。

### 与 v1 的关键区别

| 维度 | v1（废弃） | v2（当前） |
|------|-----------|-----------|
| 用户 | 教师 + 学生 | 纯教师端 |
| 题目来源 | 手动录入 | 从教师PPT中提取 + LLM生成 |
| 组卷逻辑 | 规则匹配题库 | 基于知识树的材料感知生成 |
| 知识体系 | 预定义静态列表 | 从材料中动态提取 |

### 本次范围

Phase 3（课程材料管理）+ Phase 4（知识体系构建）+ Phase 5（出卷需求与组卷）的 MVP。

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Naive UI)               │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 材料管理  │ │ 知识树    │ │ 智能组卷  │ │ 试卷管理  │   │
│  │ 上传/解析 │ │ 审核/编辑 │ │ 需求向导  │ │ 预览/导出 │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API
┌───────────────────────┴─────────────────────────────────┐
│                   后端 (FastAPI)                         │
│                                                         │
│  /api/materials    材料上传、解析、列表                     │
│  /api/knowledge    知识树提取、CRUD                       │
│  /api/questions    种子题库管理                           │
│  /api/exams        组卷需求 → 生成试卷 → 导出              │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ LLM Adapter │  │ File Parser  │  │ Export Engine │   │
│  │ DeepSeek /  │  │ PPTX/DOCX/   │  │ Word / PDF    │   │
│  │ Ollama      │  │ PDF/MD       │  │               │   │
│  └─────────────┘  └──────────────┘  └───────────────┘   │
│                                                         │
│  ┌──────────┐  ┌──────────┐                             │
│  │  SQLite  │  │  文件存储  │                             │
│  └──────────┘  └──────────┘                             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 前端 | Vue 3 + Naive UI | 已有脚手架，树/表格/表单组件齐全 |
| 后端 | FastAPI + SQLAlchemy | 已有骨架，异步支持好 |
| 数据库 | SQLite | 本地部署零配置 |
| 文件解析 | python-pptx + python-docx + PyMuPDF | PPT/DOCX/PDF 全覆盖 |
| LLM 主力 | DeepSeek API | 性价比高，中文能力强 |
| LLM 兜底 | Ollama (本地 4060) | 离线可用 |
| 导出 | python-docx (+ reportlab 可选) | Word 优先，PDF 按需 |

### 2.3 部署方式

混合模式：后端 + SQLite + 文件存储本地运行，LLM 调 DeepSeek API（通过 LLM Adapter 切换 Ollama 兜底）。

---

## 3. 数据模型

### 3.1 材料表 (materials)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| filename | VARCHAR(200) | 原始文件名 |
| file_type | VARCHAR(10) | pptx / docx / pdf / md |
| file_path | VARCHAR(500) | 本地存储路径 |
| chapter | INTEGER | 章节号 (可为空) |
| content_md | TEXT | 解析后的 Markdown 全文 |
| page_count | INTEGER | 页数/幻灯片数 |
| uploaded_at | DATETIME | 上传时间 |

### 3.2 知识树节点表 (knowledge_nodes)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| material_id | INTEGER FK | 来源材料 |
| parent_id | INTEGER | 父节点 (NULL=根) |
| sort_order | INTEGER | 同级排序 |
| name | VARCHAR(200) | 节点名称 |
| node_type | VARCHAR(20) | chapter / section / point |
| definition | TEXT | 该知识点的定义（取自材料原文） |
| key_terms | JSON | 关键术语列表 |
| teaching_emphasis | TEXT | 教学重点 |
| source_text | TEXT | 提取依据的原文片段 |
| created_at | DATETIME | |

### 3.3 种子题库表 (seed_questions)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| type | VARCHAR(20) | choice / fill / tf / short_answer / code |
| difficulty | INTEGER | 1-5 |
| knowledge_point_ids | JSON | 关联的知识点ID列表 |
| content | TEXT | 题干 |
| options | JSON | 选项 (仅选择题) |
| answer | TEXT | 正确答案 |
| explanation | TEXT | 解题思路 |
| source | VARCHAR(20) | ppt_extracted / llm_generated / manual |
| material_id | INTEGER FK | 来源材料 |
| created_at | DATETIME | |

### 3.4 试卷表 (exams)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| title | VARCHAR(200) | 试卷名称 |
| requirements_json | JSON | 组卷需求快照 |
| knowledge_snapshot_json | JSON | 组卷时知识树快照 |
| status | VARCHAR(10) | draft / reviewed / exported |
| total_score | INTEGER | 总分 |
| duration | INTEGER | 考试时长 (分钟) |
| created_at | DATETIME | |

### 3.5 试卷-题目表 (exam_questions)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| exam_id | INTEGER FK | |
| question_id | INTEGER FK | |
| score | INTEGER | 本题分值 |
| sort_order | INTEGER | 排序 |

---

## 4. 核心 Pipeline

### 4.1 材料上传 → 解析

```
教师选择文件 (pptx/docx/pdf)
  → 后端保存原始文件
  → 文件解析器提取文本 (python-pptx / python-docx / PyMuPDF)
  → 转为 Markdown 存入 content_md
  → 返回解析预览 (前 500 字符)
```

### 4.2 知识提取 → 知识树

```
触发: 教师点击"提取知识树"
  → 后端取材料的 content_md
  → 分片发送给 LLM:
      Prompt: "提取以下教学材料的章/节/知识点三层结构。
               对每个知识点，提供: 名称、定义、关键术语、教学重点。
               输出JSON格式"
  → 解析 LLM 返回的 JSON
  → 写入 knowledge_nodes 表（级联删除旧数据，重新生成）
  → 前端树组件展示
```

**LLM 输出格式协议:**
```json
{
  "chapters": [{
    "name": "第5章 树和二叉树",
    "sections": [{
      "name": "5.4 遍历二叉树",
      "points": [{
        "name": "先序遍历 (DLR)",
        "definition": "若二叉树为空则空操作；否则访问根结点，先序遍历左子树，先序遍历右子树",
        "key_terms": ["先序遍历", "DLR", "根左右"],
        "teaching_emphasis": "递归实现，口诀 DLR"
      }]
    }]
  }]
}
```

### 4.3 种子题提取

```
触发: 知识树提取完成后自动执行
  → 扫描 content_md 中的题目区域
     (识别 "单选题" / "填空题" / "算法设计题" 等标记)
  → 对无法程序化提取的题目，LLM 辅助结构化
  → 写入 seed_questions 表
  → 关联对应的 knowledge_point_ids
```

### 4.4 出卷需求向导

教师填写结构化表单：

| 分类 | 字段 | 说明 |
|------|------|------|
| 基本信息 | 试卷名称 | |
| | 考试时长 (分钟) | |
| | 总分 | |
| 范围选择 | 勾选知识树节点 | 树形多选 |
| 题型配比 | 选择题 N 道 | |
| | 填空题 N 道 | |
| | 判断题 N 道 | |
| | 简答题 N 道 | |
| | 算法设计题 N 道 | |
| 难度分布 | 1星 ~ 5星 占比 | 百分比滑块，和为 100% |
| 重点方向 | 文本框 | 自由补充 |

### 4.5 智能组卷

```
输入: 教师需求 JSON + 知识树 JSON
  →
步骤1: 种子库匹配 (选择题/填空题/判断题)
  → 按知识点 + 难度筛选 seed_questions
  → 不足时，调用 LLM 补全
  →
步骤2: LLM 生成 (简答题/算法设计题)
  → Prompt 注入知识点定义 + 术语 + 解题步骤 → 生成题目
  →
步骤3: 合卷
  → 按题型分组排序
  → 分配分值
  → 计算难度分布是否符合要求
  →
输出: 试卷 draft
```

**LLM 生成 Prompt 模板:**
```
System: 你是《数据结构》课程出题专家。以下是教学材料中的定义和解题方法，
       你生成的题目必须严格遵循这些定义和术语：
       [注入选中知识点的 definition + key_terms + teaching_emphasis + 原文示例]

User:   请生成 {题型}，考查知识点 [{知识点列表}]，难度 {1-5}，数量 {N} 道。
       要求：
       1. 专业术语必须与材料一致
       2. 解题步骤必须采用材料中的方法
       3. 输出格式为JSON
```

### 4.6 试卷预览 → 导出

```
预览:
  → 题目列表 (可拖拽排序)
  → 逐题: 替换 / 删除 / 修改分值 / 编辑题干
  → 确认 → 状态变为 reviewed

导出:
  → python-docx 生成 Word
  → 含答案版 / 无答案版
  → 标准试卷排版 (密封线、考号、题型分组)
```

---

## 5. API 设计

### 5.1 材料管理 `/api/materials`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/materials/upload` | 上传文件 → 解析 → 入库 |
| GET | `/materials` | 材料列表 |
| GET | `/materials/{id}` | 查看解析后的内容 |
| DELETE | `/materials/{id}` | 删除材料 |

### 5.2 知识树 `/api/knowledge`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/knowledge/extract/{material_id}` | 触发 LLM 知识提取 |
| GET | `/knowledge/tree/{material_id}` | 获取知识树 JSON |
| PUT | `/knowledge/nodes/{id}` | 教师编辑节点 (改名/调顺序/增删) |
| DELETE | `/knowledge/tree/{material_id}` | 删除知识树 |

### 5.3 种子题 `/api/questions`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/questions/extract/{material_id}` | 提取材料中的题目 |
| GET | `/questions` | 题库列表 (支持知识点/难度/题型筛选) |
| PUT | `/questions/{id}` | 编辑题目 |
| DELETE | `/questions/{id}` | 删除题目 |

### 5.4 试卷 `/api/exams`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/exams/generate` | 提交需求 → 生成试卷 |
| GET | `/exams` | 试卷列表 |
| GET | `/exams/{id}` | 试卷详情 (含所有题目) |
| PUT | `/exams/{id}/questions/{qid}` | 替换/修改某题 |
| GET | `/exams/{id}/export` | 导出 Word |

---

## 6. 前端路由与页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 材料列表 + 快捷操作 |
| `/materials/upload` | 材料上传 | 拖拽上传 + 解析进度 |
| `/materials/:id` | 材料详情 | 解析后 Markdown 预览 |
| `/knowledge/:materialId` | 知识树 | 树组件 + 节点编辑 + 提取种子题 |
| `/exams/create` | 组卷向导 | 多步表单 |
| `/exams/:id` | 试卷预览 | 题目列表 + 逐题操作 |
| `/exams` | 试卷管理 | 历史试卷列表 |

---

## 7. LLM Adapter 设计

```python
class LLMAdapter:
    """统一LLM调用接口，支持 DeepSeek API 和 Ollama 切换"""

    def __init__(self, provider: str = "deepseek"):
        self.provider = provider  # "deepseek" | "ollama"

    async def chat(self, system_prompt: str, user_prompt: str,
                   response_format: str = "json") -> str:
        """发送对话请求，返回响应文本"""

    async def extract_knowledge_tree(self, markdown_content: str) -> dict:
        """特化接口：从Markdown材料中提取知识树"""

    async def extract_questions(self, markdown_content: str) -> list[dict]:
        """特化接口：从Markdown材料中提取结构化题目"""

    async def generate_questions(self, context: dict, requirements: dict) -> list[dict]:
        """特化接口：基于知识上下文生成新题目"""
```

---

## 8. 文件解析器设计

```python
class FileParser:
    """多格式解析，统一输出 Markdown"""

    def parse(self, file_path: str, file_type: str) -> str:
        """
        pptx → python-pptx 提取文本框 + 备注
        docx → python-docx 提取段落 + 表格
        pdf  → PyMuPDF 提取文本
        返回: Markdown 字符串
        """
```

---

## 9. 导出引擎

```python
class ExamExporter:
    """试卷导出"""

    def export_word(self, exam_id: int, with_answer: bool = False) -> bytes:
        """
        使用 python-docx 生成:
        - 试卷头 (密封线、姓名、学号、班级)
        - 按题型分组排版
        - with_answer=True 时附加答案页
        """
```

---

## 10. 自检清单

- [x] 无 TBD / TODO 占位符
- [x] API 设计与数据模型一致
- [x] 前端路由覆盖所有功能
- [x] LLM Prompt 策略明确（注入材料原文 + 格式协议）
- [x] 知识树支持动态生成 + 教师手动编辑
- [x] 组卷 Pipeline 清晰（种子匹配 + LLM 生成 + 合卷）
- [x] 支持 DeepSeek / Ollama 双切换
- [x] v1 代码中可复用部分明确 (前端脚手架、后端骨架、导出模块)
- [x] 不含学生端功能
