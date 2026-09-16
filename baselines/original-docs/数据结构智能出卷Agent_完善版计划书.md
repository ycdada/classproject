# 数据结构智能出卷 Agent 完善版计划书（v2.0 LangGraph 重构）

**目标**：对照简历上写的"v2.0 用 LangGraph 重构 Agent 编排"，逐项落地为可运行的代码。
**原则**：最小化改动——复用现有 RAGService / ExamGenerator / KnowledgeService，新增 agent_v2 目录。
**时间**：7 天（每天 2-3 小时）。

---

## 一、简历承诺清单 → 落地任务

| 简历上写的 | 对应开发任务 | Phase | 预计耗时 |
|---|---|---|---|
| 用 LangGraph StateGraph 重构为状态机编排 | 定义 AgentState + 节点 + 条件边，编译 Graph | Phase 1 | 2天 |
| 条件边实现意图路由，替代手工 if-else | router_node + conditional_edges | Phase 1 | 含在Phase1 |
| 引入 Checkpoint 持久化，支持断线续聊 | SqliteSaver / MemorySaver 检查点 | Phase 2 | 2天 |
| interrupt 人机协同节点，组卷后人工审核 | interrupt() 暂停 + resume 恢复 | Phase 3 | 2天 |
| 流式输出 + SSE | 复用现有 ChatService 的 SSE，接入新 Graph | Phase 4 | 1天 |

---

## Phase 1：LangGraph 基础版（第 1-2 天）

### 1.1 新建目录结构

```
project_root/
├── agent_v2/                ← 新增目录，不动现有代码
│   ├── __init__.py
│   ├── state.py             ← AgentState 定义
│   ├── tools.py             ← 工具函数（复用现有服务）
│   ├── nodes.py             ← 节点函数
│   ├── graph.py             ← Graph 编译
│   └── main.py              ← 测试入口
├── backend/                 ← 现有代码不动
│   └── app/services/...
```

### 1.2 state.py —— 定义状态

**文件：`agent_v2/state.py`**

```python
from typing import Annotated, TypedDict, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """Agent 对话状态"""
    messages: Annotated[list, add_messages]  # 对话历史（自动追加）
    tool_result: Optional[dict]               # 工具执行结果
    exam_paper: Optional[dict]                # 组卷结果（待人工审核）
    review_status: Optional[str]              # 审核状态：pending / approved / rejected
    next_action: Optional[str]                # 路由标记：search / generate / knowledge / chat
```

### 1.3 tools.py —— 工具函数（复用现有服务）

**文件：`agent_v2/tools.py`**

```python
from langchain_core.tools import tool
from app.services.rag_service import RAGService
from app.services.exam_generator import ExamGenerator
from app.services.knowledge_service import KnowledgeService

rag_service = RAGService()
exam_generator = ExamGenerator()
knowledge_service = KnowledgeService()

@tool
def search_questions(query: str, question_type: str = None, difficulty: int = None) -> dict:
    """语义搜题：根据用户描述检索题库中的相关题目"""
    filters = {}
    if question_type:
        filters["question_type"] = question_type
    if difficulty is not None:
        filters["difficulty"] = difficulty
    results = rag_service.search(query, top_k=10, filters=filters)
    return {"questions": results, "count": len(results)}

@tool
def generate_exam(requirement: str, question_types: list = None,
                  difficulty_dist: dict = None, total_score: int = 100) -> dict:
    """智能组卷：根据自然语言需求生成试卷"""
    paper = exam_generator.generate(
        requirement=requirement,
        question_types=question_types,
        difficulty_dist=difficulty_dist,
        total_score=total_score
    )
    return {"exam_paper": paper, "status": "pending_review"}

@tool
def query_knowledge(chapter: str = None, keyword: str = None) -> dict:
    """知识查询：查询课程知识体系（章节/知识点）"""
    result = knowledge_service.query(chapter=chapter, keyword=keyword)
    return {"knowledge_tree": result}
```

### 1.4 nodes.py —— 节点函数

**文件：`agent_v2/nodes.py`**

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from agent_v2.tools import search_questions, generate_exam, query_knowledge

# 工具节点（LangGraph 自动处理工具调用）
tool_node = ToolNode([search_questions, generate_exam, query_knowledge])

def router_node(state):
    """意图判断节点：分析用户输入，决定走哪条路"""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    # 简单关键词路由（也可以用 LLM 判断）
    if any(kw in last_message for kw in ["搜题", "找题", "搜索", "查找"]):
        return {"next_action": "search"}
    elif any(kw in last_message for kw in ["组卷", "出卷", "生成试卷", "考试"]):
        return {"next_action": "generate"}
    elif any(kw in last_message for kw in ["知识点", "章节", "知识体系"]):
        return {"next_action": "knowledge"}
    else:
        return {"next_action": "chat"}

def chat_node(state):
    """普通对话节点：调用 LLM 生成回复"""
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="deepseek-chat", temperature=0.7)
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def should_continue(state):
    """条件边：判断是否需要调用工具"""
    if state.get("next_action") in ["search", "generate", "knowledge"]:
        return "tools"
    return "chat"
```

### 1.5 graph.py —— 编译 Graph

**文件：`agent_v2/graph.py`**

```python
from langgraph.graph import StateGraph, END
from agent_v2.state import AgentState
from agent_v2.nodes import router_node, chat_node, tool_node, should_continue

# 构建状态图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("router", router_node)
workflow.add_node("chat", chat_node)
workflow.add_node("tools", tool_node)

# 设置入口
workflow.set_entry_point("router")

# 添加条件边
workflow.add_conditional_edges(
    "router",
    should_continue,
    {
        "tools": "tools",
        "chat": "chat"
    }
)

# 工具执行完后回到 chat 生成自然语言回复
workflow.add_edge("tools", "chat")
workflow.add_edge("chat", END)

# 编译
app = workflow.compile()
```

### 1.6 main.py —— 测试入口

**文件：`agent_v2/main.py`**

```python
from agent_v2.graph import app
from langchain_core.messages import HumanMessage

# 测试 1：搜题
result = app.invoke({
    "messages": [HumanMessage(content="帮我找10道二叉树相关的选择题")]
})
print("搜题结果:", result["messages"][-1].content)

# 测试 2：组卷
result = app.invoke({
    "messages": [HumanMessage(content="帮我出一份数据结构期中考试卷，选择题10道，难度3-4")]
})
print("组卷结果:", result.get("exam_paper"))

# 测试 3：知识查询
result = app.invoke({
    "messages": [HumanMessage(content="第三章的知识点有哪些")]
})
print("知识查询:", result.get("tool_result"))
```

> **Phase 1 验收标准**
> 1. 运行 `python agent_v2/main.py`，三个测试用例都能正常返回
> 2. 搜题返回结构化题目列表
> 3. 组卷返回试卷 JSON（含题目、分数、难度分布）
> 4. 知识查询返回章节知识点树

---

## Phase 2：Checkpoint 持久化（第 3-4 天）

### 2.1 修改 graph.py，加入 Checkpoint

**文件：`agent_v2/graph.py`（更新）**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from agent_v2.state import AgentState
from agent_v2.nodes import router_node, chat_node, tool_node, should_continue

# 创建 SQLite 检查点（持久化到本地文件）
memory = SqliteSaver.from_conn_string(":memory:")  # 或 "checkpoints.db"

workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("chat", chat_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("router")
workflow.add_conditional_edges("router", should_continue, {"tools": "tools", "chat": "chat"})
workflow.add_edge("tools", "chat")
workflow.add_edge("chat", END)

# 编译时传入 checkpointer
app = workflow.compile(checkpointer=memory)
```

### 2.2 main.py 支持对话恢复

**文件：`agent_v2/main.py`（更新）**

```python
from agent_v2.graph import app
from langchain_core.messages import HumanMessage

# 第一次对话
config = {"configurable": {"thread_id": "user_123"}}
result1 = app.invoke(
    {"messages": [HumanMessage(content="帮我找10道二叉树相关的选择题")]},
    config=config
)
print("第一轮:", result1["messages"][-1].content)

# 模拟中断后恢复
result2 = app.invoke(
    {"messages": [HumanMessage(content="刚才找到的题目里，难度是3的有几道")]},
    config=config  # 同样的 thread_id
)
print("第二轮（恢复）:", result2["messages"][-1].content)
```

> Checkpoint 的作用：同样的 `thread_id` 调用 `app.invoke()` 时，LangGraph 会自动从 SQLite 加载之前的对话历史，实现"断线续聊"。

---

## Phase 3：interrupt 人工审核（第 5-6 天）

### 3.1 修改 state.py，加入审核状态

**文件：`agent_v2/state.py`（更新）**

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_result: Optional[dict]
    exam_paper: Optional[dict]
    review_status: Optional[str]  # pending / approved / rejected
    next_action: Optional[str]
```

### 3.2 新增 review_node 和 interrupt

**文件：`agent_v2/nodes.py`（新增）**

```python
from langgraph.types import interrupt, Command

def review_node(state):
    """人工审核节点：组卷完成后暂停，等待老师确认"""
    exam_paper = state.get("exam_paper")
    if not exam_paper:
        return {"review_status": "skipped"}

    # 暂停执行，返回试卷给老师审核
    review_result = interrupt({
        "type": "exam_review",
        "exam_paper": exam_paper,
        "message": "试卷已生成，请审核确认或调整"
    })

    # 老师确认后继续
    if review_result.get("approved"):
        return {"review_status": "approved"}
    else:
        # 老师要求调整
        adjustments = review_result.get("adjustments", "")
        return {
            "review_status": "rejected",
            "messages": [HumanMessage(content=f"请调整试卷：{adjustments}")]
        }
```

### 3.3 修改 graph.py，加入 review 节点

**文件：`agent_v2/graph.py`（更新）**

```python
from agent_v2.nodes import router_node, chat_node, tool_node, review_node, should_continue

workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("chat", chat_node)
workflow.add_node("tools", tool_node)
workflow.add_node("review", review_node)  # 新增审核节点

workflow.set_entry_point("router")
workflow.add_conditional_edges("router", should_continue, {"tools": "tools", "chat": "chat"})

# 组卷后进入审核
workflow.add_edge("tools", "review")
workflow.add_edge("review", "chat")  # 审核后继续对话
workflow.add_edge("chat", END)

app = workflow.compile(checkpointer=memory)
```

### 3.4 main.py 支持审核恢复

**文件：`agent_v2/main.py`（更新）**

```python
from agent_v2.graph import app
from langgraph.types import Command
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "user_123"}}

# 第一轮：生成试卷
result = app.invoke(
    {"messages": [HumanMessage(content="帮我出一份数据结构期中考试卷")]},
    config=config
)

# 检查是否进入审核状态
if result.get("review_status") == "pending":
    print("试卷已生成，等待审核...")

    # 模拟老师审核通过
    result2 = app.invoke(
        Command(resume={"approved": True}),
        config=config
    )
    print("审核通过:", result2["messages"][-1].content)

    # 或者老师要求调整
    # result2 = app.invoke(
    #     Command(resume={"approved": False, "adjustments": "选择题太多，减少5道"}),
    #     config=config
    # )
```

---

## Phase 4：集成进 FastAPI + SSE（第 7 天）

### 4.1 新增路由文件

**文件：`backend/app/api/v2/chat.py`（新增）**

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from agent_v2.graph import app as agent_app
from langchain_core.messages import HumanMessage
import json

router = APIRouter()

@router.post("/chat")
async def chat_v2(request: dict):
    """v2.0 对话接口：LangGraph 版本"""
    user_message = request.get("message")
    thread_id = request.get("thread_id", "default")

    config = {"configurable": {"thread_id": thread_id}}

    # 流式输出
    async def generate():
        async for event in agent_app.astream(
            {"messages": [HumanMessage(content=user_message)]},
            config=config
        ):
            for key, value in event.items():
                if key == "chat":
                    last_msg = value["messages"][-1]
                    yield f"data: {json.dumps({'type': 'text', 'content': last_msg.content})}\n\n"
                elif key == "tools":
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': value})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 4.2 注册路由

**文件：`backend/app/main.py`（修改）**

```python
from app.api.v2 import chat as chat_v2

app.include_router(chat_v2.router, prefix="/api/v2", tags=["v2"])
```

---

## 验收清单（全部打勾才算完成）

| # | 检查项 | 验证方法 | 状态 |
|---|---|---|---|
| 1 | Phase 1 三个测试用例全部通过 | 运行 `python agent_v2/main.py` | ☐ |
| 2 | 搜题返回结构化题目列表 | 检查返回的 JSON 格式 | ☐ |
| 3 | 组卷返回试卷 JSON | 检查 exam_paper 字段 | ☐ |
| 4 | 知识查询返回知识点树 | 检查 tool_result 字段 | ☐ |
| 5 | Checkpoint 持久化生效 | 同样的 thread_id 第二次调用能记住历史 | ☐ |
| 6 | interrupt 暂停成功 | 组卷后 review_status == "pending" | ☐ |
| 7 | Command(resume) 恢复成功 | 审核通过后继续执行 | ☐ |
| 8 | SSE 流式输出正常 | 前端能实时收到 text / tool_call / done 事件 | ☐ |
| 9 | v1.0 接口不受影响 | 原有 /api/chat 接口仍能正常使用 | ☐ |
| 10 | 代码提交到 GitHub | 新增 agent_v2/ 目录和 v2 路由 | ☐ |
| 11 | README 更新 | 说明 v2.0 架构变化和如何运行 | ☐ |
| 12 | 简历数字回填 | 把"v2.0用LangGraph重构"改成"已完成" | ☐ |

---

## 面试话术

### 问题 1：你的项目用了 LangGraph，能讲讲架构吗？

我把 v1.0 的手工 if-else 工具调用重构成了 LangGraph 状态机。核心是一个 StateGraph，包含四个节点：router（意图判断）、chat（对话生成）、tools（工具执行）、review（人工审核）。用户输入先进 router，通过条件边路由到不同的工具节点——搜题、组卷或知识查询。组卷完成后进入 review 节点，通过 interrupt 暂停，等老师确认后再继续。所有状态通过 Checkpoint 持久化到 SQLite，支持断线续聊。

### 问题 2：为什么用 LangGraph 而不是继续用 FastAPI 写 if-else？

v1.0 我用 FastAPI + 手工 if-else 实现了工具调用，但有两个问题：一是状态散落在各处（对话历史、工具结果、组卷状态），维护麻烦；二是想加"人工审核"功能时，手写状态机容易出 bug。LangGraph 把对话流程抽象成有向图，节点和边清晰定义，新增功能只需要加节点和条件边，不用改主干逻辑。而且 Checkpoint 自动处理状态持久化，不用自己写缓存逻辑。

### 问题 3：LangGraph 的 Checkpoint 是怎么工作的？

Checkpoint 是 LangGraph 的状态持久化机制。每次状态变更（比如调用工具、生成回复）都会自动保存到 SQLite。调用 app.invoke() 时传入同样的 thread_id，LangGraph 会从 SQLite 加载该线程的历史状态，实现对话恢复。我用的是 SqliteSaver，生产环境可以换成 PostgreSQL 或 Redis。

### 问题 4：interrupt 是怎么实现的？

interrupt 是 LangGraph 的人机协同机制。在 review 节点里调用 interrupt()，Graph 会暂停执行，把当前状态（比如生成的试卷）返回给调用方。前端拿到后展示给老师审核，老师确认后调用 Command(resume={"approved": True})，Graph 从暂停点继续执行。这个机制特别适合需要人工介入的场景，比如审批、审核、敏感操作确认。

---

**最后提醒**：跑通 Phase 1-4 后，记得把简历上的"v2.0用LangGraph重构（进行中）"改成"已完成"，并补充实际测试数据（比如对话恢复成功率、审核流程耗时）。
