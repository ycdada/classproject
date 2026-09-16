"""生成项目中期报告 Word 文档"""
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

doc = Document()

# ── 页面设置 ──
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)

# ── 样式设置 ──
style = doc.styles['Normal']
font = style.font
font.name = 'SimSun'
font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')

for level in range(1, 4):
    heading_style = doc.styles[f'Heading {level}']
    heading_style.font.name = 'SimHei'
    heading_style.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
    heading_style.font.color.rgb = RGBColor(0, 0, 0)

def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = 'SimHei'
        run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
    return h

def add_para(text, bold=False, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Pt(24)
    run = p.add_run(text)
    run.font.name = 'SimSun'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
    run.font.size = Pt(12)
    run.bold = bold
    return p

def add_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(10)
    # Data
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.rows[r + 1].cells[c]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)
    doc.add_paragraph()  # spacing
    return table

def add_bullet(text):
    p = doc.add_paragraph(style='List Bullet')
    p.clear()
    run = p.add_run(text)
    run.font.name = 'SimSun'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
    run.font.size = Pt(12)
    return p

# ============================================================
# 封面
# ============================================================
for _ in range(6):
    doc.add_paragraph()

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('数据结构智能出卷系统')
run.font.name = 'SimHei'
run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
run.font.size = Pt(28)
run.bold = True

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('项目中期报告')
run.font.name = 'SimHei'
run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
run.font.size = Pt(22)

doc.add_paragraph()
doc.add_paragraph()

members = doc.add_paragraph()
members.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = members.add_run('小组成员：陈天阳  黄睿宇  张景越  赵若涵')
run.font.name = 'SimSun'
run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
run.font.size = Pt(14)

doc.add_paragraph()

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = info.add_run(f'日期：{datetime.date.today().strftime("%Y年%m月%d日")}')
run.font.name = 'SimSun'
run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
run.font.size = Pt(14)

doc.add_page_break()

# ============================================================
# 目录页（手动）
# ============================================================
add_heading('目  录', level=1)
toc_items = [
    ('一、技术路线', '技术选型与整体开发路线'),
    ('二、系统架构', '前后端架构、模块划分、数据流'),
    ('三、功能设计', '核心功能模块详细设计'),
    ('四、分工情况', '团队成员分工'),
    ('五、当前进展', '已完成任务与开发进度'),
    ('六、系统演示', '主要界面说明'),
    ('七、后续安排', '里程碑、未完成工作与时间规划'),
    ('八、风险管理', '风险识别与应对策略'),
    ('九、重难点分析', '关键技术难点与解决方案'),
]
for title_text, desc in toc_items:
    p = doc.add_paragraph()
    run = p.add_run(f'{title_text}')
    run.font.name = 'SimHei'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
    run.font.size = Pt(14)
    run.bold = True
    run2 = p.add_run(f'  —— {desc}')
    run2.font.size = Pt(11)
    run2.font.color.rgb = RGBColor(100, 100, 100)

doc.add_page_break()

# ============================================================
# 一、技术路线
# ============================================================
add_heading('一、技术路线', level=1)

add_heading('1.1 项目背景', level=2)
add_para('在高校《数据结构》课程教学中，出卷是教师一项高频且费时的工作。传统出卷方式面临以下痛点：', indent=True)
add_bullet('效率低下：教师需从大量教学材料中手动梳理知识点，逐题编写、排版，耗费大量时间')
add_bullet('质量不稳定：试卷质量高度依赖教师个人经验，难以保证知识点覆盖度和难度分布的合理性')
add_bullet('教考分离：出题与教学内容脱节，容易出现考非所教的问题')
add_bullet('复用困难：历史试卷和题库缺乏系统管理，题目检索和复用效率低')
add_para('本系统旨在利用大语言模型（LLM）与检索增强生成（RAG）技术，构建一个面向《数据结构》课程的智能出卷系统。帮助教师从教学材料中自动提取知识体系，根据出卷需求智能组卷，显著提升出卷效率和试卷质量。系统采用纯教师端 Web 应用模式，本地部署，数据完全本地化。', indent=True)

add_heading('1.2 技术选型', level=2)
add_table(
    ['层次', '技术', '选型理由'],
    [
        ['后端框架', 'FastAPI (Python)', '异步高性能，原生支持 SSE 流式响应'],
        ['ORM', 'SQLAlchemy 2.0 (Async)', '异步数据库操作，与 FastAPI 深度集成'],
        ['数据库', 'SQLite (aiosqlite)', '轻量免安装，适合单机教师端部署'],
        ['向量数据库', 'ChromaDB', '轻量级持久化向量存储，内嵌部署无需额外服务'],
        ['大语言模型', 'DeepSeek API (deepseek-chat)', '国产高性价比，OpenAI 兼容接口，中文能力强'],
        ['嵌入模型', 'BAAI/bge-small-zh-v1.5', '开源中文嵌入模型（512维），本地运行零成本'],
        ['文件解析', 'python-pptx / python-docx / PyMuPDF', '支持 PPT/Word/PDF 多格式教学材料解析'],
        ['文档导出', 'python-docx', '生成标准 Word 试卷文档'],
        ['前端框架', 'Vue 3 + Vite', '响应式 UI，组件化开发'],
        ['UI 组件库', 'Naive UI', 'TypeScript 原生、暗色模式、Tree 组件适合知识树'],
        ['状态管理', 'Pinia', 'Vue 3 官方推荐，轻量简洁'],
        ['AI 对话', 'SSE (Server-Sent Events)', '单向长连接流式推送，比 WebSocket 更轻量'],
    ],
)

add_heading('1.3 开发路线', level=2)
add_para('项目采用"敏捷迭代 + 模块化并行"开发策略，分为三个阶段：', indent=True)
add_bullet('第一阶段（基础设施）：搭建 FastAPI + Vue 3 项目骨架，完成数据模型设计与 CRUD API')
add_bullet('第二阶段（核心功能）：实现材料上传解析、知识树 LLM 提取、RAG 语义检索、智能组卷流水线')
add_bullet('第三阶段（完善体验）：集成 AI 对话助手、DOCX 试卷导出、Bug 修复与嵌入模型切换')

doc.add_page_break()

# ============================================================
# 二、系统架构
# ============================================================
add_heading('二、系统架构', level=1)

add_heading('2.1 整体架构', level=2)
add_para('系统采用经典的前后端分离架构，后端提供 RESTful API + SSE 流式接口，前端通过 Axios 进行 HTTP 通信。整体架构分为四层：', indent=True)

add_table(
    ['层级', '组件', '职责'],
    [
        ['表现层', 'Vue 3 + Naive UI + Pinia', '教师交互界面、知识树可视化、AI 对话面板'],
        ['接口层', 'FastAPI Routers', 'RESTful API 路由、请求校验、SSE 流式端点'],
        ['业务层', 'Service 模块', '题服务、组卷流水线、RAG 检索、LLM 适配、文件解析'],
        ['数据层', 'SQLite + ChromaDB', '关系数据持久化、向量嵌入存储与语义检索'],
    ],
)

add_heading('2.2 模块架构', level=2)
add_para('后端按职责划分为 6 个核心模块：', indent=True)

add_table(
    ['模块', '核心类/文件', '功能说明'],
    [
        ['LLM 适配器', 'llm_adapter.py / LLMAdapter', '统一 DeepSeek API 调用接口：对话、流式、嵌入、Function Calling'],
        ['RAG 流水线', 'rag.py / RAGPipeline', 'ChromaDB 向量增删查、余弦相似度语义检索'],
        ['文件解析器', 'file_parser.py / FileParser', 'PPTX/DOCX/PDF/MD → Markdown 统一输出'],
        ['组卷生成器', 'exam_generator.py / ExamGenerator', '种子题库匹配 + LLM 补充的混合组卷'],
        ['题服务', 'question_service.py / QuestionService', 'CRUD + 自动向量化 + RAG 同步 + 语义搜索'],
        ['导出服务', 'docx_export.py + export_service.py', 'Word 试卷文档生成（含/不含答案）'],
    ],
)

add_heading('2.3 数据流', level=2)
add_para('核心业务流程数据流如下：', indent=True)

add_para('【材料 → 知识树】', bold=True)
add_para('教师上传 PPTX/DOCX/PDF → FileParser 解析为 Markdown → LLM 提取章/节/知识点三层树 → 存入 KnowledgeNode 表', indent=True)

add_para('【题库 → 向量化】', bold=True)
add_para('题目创建/导入 → LLMAdapter.embed() 调用本地 BGE 模型生成 512 维向量 → RAGPipeline.add_question() 存入 ChromaDB', indent=True)

add_para('【组卷流程】', bold=True)
add_para('教师选择知识点 + 题型配比 + 难度分布 → ExamGenerator 优先从题库语义匹配 → 不足时 LLM 补充 → 创建 Exam + ExamQuestion 关联记录', indent=True)

add_para('【AI 对话】', bold=True)
add_para('前端 SSE 连接 → Chat Service 构建对话上下文 → DeepSeek API 流式返回 → 前端逐字渲染', indent=True)

doc.add_page_break()

# ============================================================
# 三、功能设计
# ============================================================
add_heading('三、功能设计', level=1)

add_heading('3.1 功能模块总览', level=2)
add_table(
    ['模块', '功能点', '说明'],
    [
        ['首页概览', '统计面板 + 快捷入口', '展示材料数、题目数、试卷数；一键跳转上传/组卷'],
        ['材料管理', '上传 / 解析 / 预览 / 删除', '支持 PPTX/DOCX/PDF/MD 四种格式自动解析为 Markdown'],
        ['知识树', 'LLM 提取 / 树形展示 / 节点勾选', '三层知识结构（章→节→点），支持节点详情查看和手动修正'],
        ['题库管理', 'CRUD / 筛选 / 批量导入 / 语义搜索', '五类题型（选择/填空/判断/简答/算法），RAG 语义检索相似题'],
        ['智能组卷', '组卷向导 / 混合生成', '知识点选择 + 题型配比 + 难度分布 → 种子匹配 + LLM 补充'],
        ['试卷管理', '列表 / 预览 / 替换题目 / 导出', '答案折叠查看、单题替换、DOCX 导出（含/不含答案）'],
        ['AI 助手', '流式对话 / FAB 浮动入口', 'SSE 流式响应、多轮对话上下文、右下角浮动按钮快捷唤起'],
    ],
)

add_heading('3.2 题库管理', level=2)
add_para('支持五种题型：选择题（choice）、填空题（fill）、判断题（tf）、简答题（short_answer）、算法设计题（code）。每题关联章节、知识点、难度（1-5星）、选项（选择题为 dict 格式）、答案和解析。', indent=True)
add_para('批量导入支持 JSON 和 Excel 两种格式，自动解析字段映射。题目创建/编辑时自动调用嵌入模型生成向量并同步至 ChromaDB，实现语义级别的相似题检索。', indent=True)

add_heading('3.3 材料与知识树', level=2)
add_para('教师上传教学材料（PPT/教案/PDF）后，系统自动调用 FileParser 解析为 Markdown 文本。随后通过 LLM（DeepSeek）提取三层知识结构：章（chapter）→ 节（section）→ 知识点（point），每个知识点节点保留原文定义、关键术语和教学重点。', indent=True)
add_para('教师可在知识树页面查看、勾选知识点，手动修正节点内容后直接跳转组卷向导，所选知识点 ID 自动带入组卷参数。', indent=True)

add_heading('3.4 智能组卷', level=2)
add_para('组卷采用"种子题库优先 + LLM 补充"的混合策略：', indent=True)
add_bullet('种子匹配：根据题型、知识点覆盖、难度要求从 SQLite 题库中筛选题目')
add_bullet('LLM 补充：当种子题库中某类题目数量不足时，调用 DeepSeek API 生成新题')
add_bullet('知识注入：生成的题目必须严格遵循材料中的定义和术语，避免概念偏差')
add_para('组卷向导提供可视化表单：试卷名称、时长、总分、五种题型数量配比、5 级难度百分比分布、重点方向备注。', indent=True)

add_heading('3.5 AI 对话助手', level=2)
add_para('系统右下角常驻浮动按钮（FAB），点击展开右侧聊天面板。基于 DeepSeek API，SSE 流式推送响应，支持多轮对话上下文记忆。系统预设为"数据结构教学助手"角色，可辅助教师解答组卷策略、知识点讲解、题目解析等教学场景问题。', indent=True)

doc.add_page_break()

# ============================================================
# 四、分工情况
# ============================================================
add_heading('四、分工情况', level=1)

add_para('本项目由四位团队成员协作完成，具体分工如下：', indent=True)
add_table(
    ['成员', '角色', '负责模块'],
    [
        ['陈天阳', '后端架构 + LLM', 'FastAPI 架构设计、LLM 适配器（DeepSeek 对话 + 本地嵌入）、RAG 流水线（ChromaDB）、文件解析器（PPTX/DOCX/PDF/MD）、组卷生成器（种子匹配+LLM补充）'],
        ['黄睿宇', '后端业务 + 数据', '数据模型设计（Question/Exam/Material/KnowledgeNode）、Pydantic Schemas、Materials API、Knowledge Tree API、Questions API（含RAG同步）、Exams API（含DOCX导出）、Chat Service'],
        ['张景越', '前端架构 + 页面', 'Vue 3 项目搭建（Vite+Naive UI+Pinia）、路由设计、首页概览 Dashboard、题库管理 QuestionBank（含语义搜索）、材料上传 MaterialUpload、材料详情 MaterialDetail、知识树 KnowledgeTree'],
        ['赵若涵', '前端组件 + 交互', '组卷向导 ExamWizard、试卷预览 ExamPreview、AI 对话面板 AIChatDialog（SSE流式+FAB浮动按钮）、知识树面板 KnowledgeTreePanel、试卷列表 ExamList、项目文档与计划书撰写'],
    ],
)

doc.add_page_break()

# ============================================================
# 五、当前进展
# ============================================================
add_heading('五、当前进展', level=1)

add_heading('5.1 整体进度', level=2)
add_para('截至目前，项目已完成全部 15 个开发任务的代码实现，整体进度约 95%。剩余工作主要为测试优化和文档完善。', indent=True)

add_heading('5.2 已完成任务清单', level=2)
add_table(
    ['#', '任务', '状态', '关键产出'],
    [
        ['1', '清理 v1 学生端代码', '✅', '删除 17 个文件，重写 main.py 和路由'],
        ['2', '重构数据模型', '✅', 'Question/Exam/Material/KnowledgeNode 四表'],
        ['3', '简化配置（DeepSeek Only）', '✅', 'config.py 精简为 6 个配置项'],
        ['4', '文件解析服务', '✅', 'FileParser — PPTX/DOCX/PDF/MD 四格式'],
        ['5', 'LLM 适配器', '✅', 'DeepSeek 对话 + 本地 BGE 嵌入'],
        ['6', 'RAG 流水线', '✅', 'ChromaDB 向量增删查 + 语义检索'],
        ['7', 'Pydantic Schemas', '✅', 'Material/KnowledgeNode/Question/Exam schema'],
        ['8', 'Materials API', '✅', '上传/解析/列表/详情/删除 CRUD'],
        ['9', 'Knowledge Tree API', '✅', 'LLM 提取/树查询/节点编辑/删除'],
        ['10', 'Question Service + RAG 同步', '✅', 'CRUD + 自动向量化 + 语义搜索端点'],
        ['11', '考试生成 + DOCX 导出', '✅', '混合组卷 + Word 导出（含/不含答案）'],
        ['12', 'AI Chat API', '✅', 'SSE 流式对话 + 多轮上下文'],
        ['13', '前端 API 客户端', '✅', 'Materials/Knowledge/Exams/Questions API'],
        ['14', '前端页面（8 个 + 组件）', '✅', '全部教师端页面 + AI 对话框'],
        ['15', '嵌入 API 修复', '✅', '本地 BGE-small-zh-v1.5 替代 DeepSeek'],
    ],
)

add_heading('5.3 代码统计', level=2)
add_table(
    ['类别', '文件数', '代码行数（估算）'],
    [
        ['后端 Python', '~30', '~3500'],
        ['前端 Vue/JS', '~25', '~2800'],
        ['配置文件', '~5', '~100'],
        ['文档', '~3', '~800'],
        ['合计', '~63', '~7200'],
    ],
)

doc.add_page_break()

# ============================================================
# 六、系统演示
# ============================================================
add_heading('六、系统演示', level=1)

add_heading('6.1 首页概览', level=2)
add_para('左侧导航栏包含五个入口：首页概览、题库管理、材料管理、知识树、试卷管理。首页展示材料库列表（文件名、类型、上传时间）和历史试卷列表（名称、状态、总分、时长），提供"上传材料"和"智能组卷"快捷按钮。', indent=True)

add_heading('6.2 材料上传与解析', level=2)
add_para('在材料管理页面上传 PPTX/DOCX/PDF/MD 文件，系统自动调用 FileParser 解析为 Markdown 文本，存入数据库。解析完成后显示文件名、页数和类型，提供"查看知识树"快捷跳转。', indent=True)

add_heading('6.3 知识树提取', level=2)
add_para('点击"提取知识树"按钮，系统将材料 Markdown 发送至 DeepSeek API，由 LLM 识别章/节/知识点三层结构。提取结果以树形组件展示（NTree），左侧勾选知识点、右侧查看节点详情（定义、术语、教学重点）。勾选知识点后可直接跳转组卷向导。', indent=True)

add_heading('6.4 智能组卷', level=2)
add_para('组卷向导提供可视化表单：填写试卷名称、时长（分钟）、总分，配置五种题型数量、五级难度百分比分布，填写重点方向备注。确认后调用组卷生成器，优先从种子题库匹配已有题目，不足时调用 LLM 补充，生成完整试卷。', indent=True)

add_heading('6.5 试卷预览与导出', level=2)
add_para('试卷预览页展示全部题目列表（编号、题型、分值、题干、选项）。答案默认折叠，点击展开可查看正确答案和解析。提供"导出试卷"和"导出(含答案)"两个按钮，生成标准格式的 Word (.docx) 文档供打印使用。', indent=True)

add_heading('6.6 AI 对话助手', level=2)
add_para('右下角常驻蓝色圆形浮动按钮（FAB），点击展开右侧聊天侧边栏。支持 SSE 流式响应（打字机效果），多轮对话上下文记忆。教师可向 AI 助手咨询组卷策略、知识点讲解、题目解析等教学问题。', indent=True)

add_heading('6.7 语义搜索', level=2)
add_para('题库管理页面顶部搜索框输入关键词（如"树的遍历"），后端通过本地 BGE 嵌入模型生成查询向量，在 ChromaDB 中执行余弦相似度检索，返回语义相近的题目列表（按相似度排序），支持按题型、难度、章节筛选。', indent=True)

doc.add_page_break()

# ============================================================
# 七、后续安排
# ============================================================
add_heading('七、后续安排', level=1)

add_heading('7.1 里程碑达成情况', level=2)
add_table(
    ['里程碑', '目标', '状态'],
    [
        ['M1 - 需求冻结', '需求分析、系统设计文档、原型设计', '✅ 已完成'],
        ['M2 - 技术验证', '核心 AI 能力（LLM 知识提取/组卷）原型验证通过', '✅ 已完成'],
        ['M3 - MVP 可用', '端到端流程跑通：上传材料→生成试卷→预览导出', '✅ 已完成'],
        ['M4 - 功能完备', '全部功能模块开发完成', '🔄 进行中（~95%）'],
        ['M5 - 交付上线', '系统通过验收测试，交付使用', '⏳ 待开始'],
    ],
)

add_heading('7.2 待完成工作', level=2)
add_table(
    ['#', '任务', '优先级', '预计耗时'],
    [
        ['1', '材料列表页缺少入口（/materials 独立页）', '中', '2h'],
        ['2', '知识树节点详情交互优化（点击展开编辑）', '中', '3h'],
        ['3', '组卷向导——难度百分比校验（总和 100%）', '中', '1h'],
        ['4', '题库搜索增加知识点标签筛选', '低', '2h'],
        ['5', '修复 ChromaDB 嵌入同步的潜在并发问题', '低', '2h'],
        ['6', '端到端集成测试与 Bug 修复', '高', '1d'],
        ['7', '部署文档 + README 完善', '高', '3h'],
        ['8', '演示 PPT 制作', '高', '4h'],
    ],
)

add_heading('7.3 时间规划', level=2)
add_table(
    ['时间段', '工作内容'],
    [
        ['第 1 周', '完成剩余功能点修复、集成测试'],
        ['第 2 周', '文档完善、部署说明、演示 PPT'],
        ['第 3 周', '答辩准备、演示演练'],
    ],
)

doc.add_page_break()

# ============================================================
# 八、风险管理
# ============================================================
add_heading('八、风险管理', level=1)

add_para('项目开展过程中已识别以下主要风险，并制定了应对策略：', indent=True)

add_table(
    ['风险编号', '风险描述', '影响', '概率', '应对策略', '当前状态'],
    [
        ['R1', 'LLM 接口调用不稳定或成本过高', '高', '中', '设计 LLM 适配层支持多模型切换；关键路径准备规则引擎兜底', '✅ 已化解 — DeepSeek API 稳定，成本可控'],
        ['R2', '教学材料格式多样，解析质量不达标', '高', '高', '分格式设计解析器；支持人工校正补充', '✅ 已化解 — 四格式解析器实现完毕'],
        ['R3', '知识提取准确率不足，影响试卷质量', '高', '中', '引入教师人工审核环节；提供节点手动修正接口', '✅ 已化解 — 知识树支持手动编辑'],
        ['R4', '单机环境性能瓶颈', '中', '中', '大文件异步处理；嵌入模型使用轻量本地方案', '✅ 已化解 — BGE-small 24MB 模型本地运行'],
        ['R5', 'DeepSeek 不提供嵌入 API（中期发现）', '高', '—', '切换为本地 SentenceTransformer 模型', '✅ 已解决 — BAAI/bge-small-zh-v1.5'],
    ],
)

doc.add_page_break()

# ============================================================
# 九、重难点分析
# ============================================================
add_heading('九、重难点分析', level=1)

add_heading('8.1 LLM 适配与嵌入模型切换', level=2)
add_para('【难点】DeepSeek API 采用 OpenAI 兼容接口，但其功能边界不明确。开发过程中发现 DeepSeek 不提供 Embedding API（/v1/embeddings 返回 404），导致向量化功能无法工作。', indent=True)
add_para('【解决方案】将嵌入从远程 API 切换为本地模型。选择 BAAI/bge-small-zh-v1.5（24MB, 512 维），通过 sentence-transformers 库加载，使用 asyncio.to_thread() 将同步 encode 包装为异步非阻塞调用。采用 local_files_only=True 优先从缓存加载，避免网络依赖。首次下载通过 HF_ENDPOINT=hf-mirror.com 使用国内镜像。', indent=True)

add_heading('8.2 RAG 语义检索的精确度', level=2)
add_para('【难点】简单的关键词匹配无法捕捉题目之间的语义关联（如"二叉树遍历"与"前序遍历"的关联关系）。ChromaDB 默认参数可能导致检索结果不稳定。', indent=True)
add_para('【解决方案】将题目按"题干 + 选项 + 知识点 + 章节"拼接为统一文本后向量化；ChromaDB 使用余弦相似度（cosine）作为距离度量；嵌入模型选用中文优化的 BGE 系列；检索时支持额外的元数据过滤（where 子句），可限定题型、难度、章节范围。', indent=True)

add_heading('8.3 知识树 LLM 提取的一致性', level=2)
add_para('【难点】LLM 输出的结构性不稳定——同一份材料多次提取可能得到不同的章节划分、知识点粒度不同、JSON 格式偶有偏差。直接使用不稳定的输出会导致知识树混乱。', indent=True)
add_para('【解决方案】设计结构化 Prompt 约束输出格式（章/节/点三层 JSON schema）；解析时使用 _parse_json() 方法自动清洗 Markdown 代码块标记；提供手动编辑接口（PUT /api/knowledge/nodes/{id}），教师可修正 LLM 的不准确输出；支持"重新提取"按钮一键重建知识树。', indent=True)

add_heading('8.4 混合组卷的题目分配', level=2)
add_para('【难点】如何合理分配"种子题库匹配"和"LLM 生成"的比例？种子题库可能某些题型/难度组合缺乏题目，全依赖 LLM 则成本高、质量不稳定。', indent=True)
add_para('【解决方案】采用"种子优先"策略：先根据题型、知识点、难度从 SQLite 筛选题库中的已有题目（放宽条件获取 3 倍数量后排序）；不足的数量由 LLM 补充生成，但 LLM 生成题目前必须注入知识树的原文定义和术语作为上下文，确保生成题目的概念一致性。', indent=True)

add_heading('8.5 前端 SSE 流式对话体验', level=2)
add_para('【难点】传统 HTTP 请求-响应模式会导致 AI 对话体验生硬（需等待完整回复）。直接使用 WebSocket 增加后端复杂度。需要实现"打字机"效果的流式逐字渲染。', indent=True)
add_para('【解决方案】选择 SSE（Server-Sent Events）协议：后端 FastAPI 使用 StreamingResponse + async generator 逐块推送；前端通过 EventSource + ReadableStream 读取文本 delta，逐字追加到聊天消息中。相比 WebSocket，SSE 单向推送、HTTP 协议兼容、实现简单，完全满足对话场景需求。', indent=True)

add_heading('8.6 ChromaDB 与 SQLite 的数据一致性', level=2)
add_para('【难点】题目存在 SQLite 中，嵌入向量存在 ChromaDB 中，两者通过 embedding_id 关联。但 Crud 操作（创建/编辑/删除）需要在两个存储之间保持同步，任何一步失败都可能导致数据不一致。', indent=True)
add_para('【解决方案】QuestionService 封装所有 Crud 操作为事务性步骤：创建时先 flush 获取 ID → 生成嵌入 → 写入 ChromaDB → commit；更新时重新生成嵌入并覆盖 ChromaDB 记录；删除时先删 ChromaDB 再删 SQLite。提供 /api/questions/embed-all 全量重建接口，用于修复潜在的不一致。', indent=True)

# ============================================================
# 保存
# ============================================================
output_path = r'C:\Users\Xavier\Desktop\project1\docs\数据结构智能出卷系统_中期报告.docx'
doc.save(output_path)
print(f'报告已生成: {output_path}')
