"""agent_v2 节点 — 意图路由 / 工具执行 / 人工审核 / 对话生成。

所有节点为同步函数（Python 3.10 + LangGraph interrupt 的约束），节点内部通过
_run() 包装现有的异步服务。意图路由用 LLM function calling 判断（替代关键词 if-else）。
"""
import asyncio
import json

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import interrupt

from app.services.llm_adapter import LLMAdapter
from app.services.chat_service import CHAT_SYSTEM_PROMPT, TOOLS

from .tools import search_questions, generate_exam, query_knowledge


ROUTER_SYSTEM_PROMPT = """你是《数据结构》教学助手的意图路由器。阅读用户输入，判断意图并调用对应工具：

- search_questions：搜题 / 找题 / 查找题目
- generate_exam：组卷 / 出卷 / 生成试卷 / 考试
- query_knowledge：知识点 / 章节 / 概念问答

规则：
1. 只要能推断出意图，就调用对应工具，不要反问
2. 如果用户只是闲聊或无法归入上述三类，不要调用任何工具
"""


def _run(coro):
    """在同步节点内运行异步协程（每次新建独立事件循环）。"""
    return asyncio.run(coro)


async def _collect_stream(agen):
    """把异步流式生成器聚合为完整字符串。"""
    chunks = []
    async for chunk in agen:
        chunks.append(chunk)
    return "".join(chunks)


def _to_openai_messages(messages: list) -> list[dict]:
    """将 LangChain 消息列表转为 OpenAI 风格 dict 列表。"""
    out = []
    for m in messages or []:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            out.append({"role": "assistant", "content": m.content})
    return out


def router_node(state: dict) -> dict:
    """意图路由节点：LLM function calling 判断意图，产出 next_action 与 tool_args。"""
    messages = _to_openai_messages(state.get("messages", []))
    llm = LLMAdapter()
    result = _run(llm.chat_with_tools(ROUTER_SYSTEM_PROMPT, messages, TOOLS))
    if result["type"] == "tool_call":
        return {"next_action": result["name"], "tool_args": result["arguments"]}
    return {"next_action": "chat", "tool_args": None}


def route_after_router(state: dict) -> str:
    """条件边：根据路由结果分发到对应节点。"""
    return state.get("next_action", "chat")


def search_node(state: dict) -> dict:
    args = state.get("tool_args") or {}
    result = _run(search_questions(**args))
    return {"tool_result": result, "next_action": None}


def knowledge_node(state: dict) -> dict:
    args = state.get("tool_args") or {}
    result = _run(query_knowledge(**args))
    return {"tool_result": result, "next_action": None}


def generate_node(state: dict) -> dict:
    args = state.get("tool_args") or {}
    result = _run(generate_exam(**args))
    return {
        "tool_result": result,
        "exam_paper": result,
        "review_status": "pending",
        "next_action": None,
    }


def review_node(state: dict) -> dict:
    """人工审核节点：组卷完成后 interrupt 暂停，等待教师确认。"""
    exam_paper = state.get("exam_paper")
    if not exam_paper:
        return {"review_status": "skipped"}

    review_result = interrupt({
        "type": "exam_review",
        "exam_paper": exam_paper,
        "message": "试卷已生成，请审核确认或调整",
    })

    if isinstance(review_result, dict) and review_result.get("approved"):
        return {"review_status": "approved"}

    adjustments = ""
    if isinstance(review_result, dict):
        adjustments = review_result.get("adjustments", "")
    else:
        adjustments = str(review_result or "")
    return {
        "review_status": "rejected",
        "messages": [HumanMessage(content=f"请调整试卷：{adjustments}")],
    }


def chat_node(state: dict) -> dict:
    """对话节点：基于历史 + 工具结果生成自然语言回复。"""
    llm = LLMAdapter()
    messages = _to_openai_messages(state.get("messages", []))
    tool_result = state.get("tool_result")
    review_status = state.get("review_status")

    if review_status == "approved" and state.get("exam_paper"):
        payload = {
            "summary": state["exam_paper"].get("summary", ""),
            "question_count": len(state["exam_paper"].get("questions", [])),
        }
        prompt = f"试卷已通过审核，请向老师汇报结果：{json.dumps(payload, ensure_ascii=False)}"
    elif tool_result:
        prompt = f"工具执行完毕，请用自然语言向老师汇报结果：{json.dumps(tool_result, ensure_ascii=False)}"
    else:
        prompt = None

    full = messages + ([{"role": "user", "content": prompt}] if prompt else [])
    content = _run(_collect_stream(llm.chat_stream(CHAT_SYSTEM_PROMPT, full)))
    return {"messages": [AIMessage(content=content)]}
