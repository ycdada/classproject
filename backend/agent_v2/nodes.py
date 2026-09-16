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

from .tools import search_questions, query_knowledge, propose_scope, assemble_paper


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
    """组卷意图：先提出考查范围（不直接生成试卷）。"""
    args = state.get("tool_args") or {}
    title = args.get("title", "未命名试卷")
    scope_text = args.get("scope", "")
    demand = {
        "title": title,
        "teaching_progress": "",
        "exam_scope": scope_text,
        "focus_notes": "",
        "material_ids": [],
        "question_distribution": {},
        "difficulty_distribution": {},
        "total_score": args.get("total_score", 100),
        "duration": args.get("duration", 120),
    }
    result = _run(propose_scope(demand))
    return {
        "tool_result": {"scope_id": result["scope_id"], "message": "已提出考查范围，请确认"},
        "scope_id": result["scope_id"],
        "scope_status": result["status"],
        "scope_tree": result["tree"],
        "next_action": None,
    }


def propose_scope_node(state: dict) -> dict:
    """提出考查范围节点：ScopeBuilder.propose → scope_review(interrupt)。"""
    args = state.get("tool_args") or {}
    demand = args.get("demand") or {
        "title": args.get("title", "未命名试卷"),
        "teaching_progress": args.get("teaching_progress", ""),
        "exam_scope": args.get("exam_scope", ""),
        "focus_notes": args.get("focus_notes", ""),
        "material_ids": [],
        "question_distribution": args.get("question_distribution", {}),
        "difficulty_distribution": args.get("difficulty_distribution", {}),
        "total_score": args.get("total_score", 100),
        "duration": args.get("duration", 120),
    }
    result = _run(propose_scope(demand))
    return {
        "tool_result": {"scope_id": result["scope_id"], "message": "已提出考查范围，请确认"},
        "scope_id": result["scope_id"],
        "scope_status": result["status"],
        "scope_tree": result["tree"],
        "next_action": None,
    }


def scope_review_node(state: dict) -> dict:
    """考查范围审核节点：interrupt 等教师确认；确认后才装配试卷。"""
    scope_id = state.get("scope_id")
    if not scope_id:
        return {"scope_status": "skipped"}

    review = interrupt({
        "type": "scope_review",
        "scope_id": scope_id,
        "tree": state.get("scope_tree", []),
        "message": "请确认考查范围；确认后系统将按范围组卷",
    })

    if isinstance(review, dict) and review.get("confirmed"):
        from app.database import async_session
        from app.models.scope import ExamScope

        async def _confirm():
            async with async_session() as db:
                scope = await db.get(ExamScope, scope_id)
                if scope and scope.status != "confirmed":
                    scope.status = "confirmed"
                    await db.commit()

        _run(_confirm())

        demand = (state.get("tool_args") or {}).get("demand") or state.get("tool_args") or {}
        try:
            result = _run(assemble_paper(demand, scope_id))
        except ValueError as e:
            return {
                "scope_status": "confirmed",
                "tool_result": {"error": str(e), "message": "题库为空且无法拟草稿，请先维护题库或材料"},
                "next_action": None,
            }
        return {
            "scope_status": "confirmed",
            "exam_paper": result,
            "review_status": "pending",
            "next_action": None,
        }

    adjustments = review.get("adjustments", "") if isinstance(review, dict) else str(review or "")
    return {
        "scope_status": "rejected",
        "messages": [HumanMessage(content=f"请调整考查范围：{adjustments}")],
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
    scope_status = state.get("scope_status")

    if review_status == "approved" and state.get("exam_paper"):
        paper = state["exam_paper"]
        payload = {
            "summary": paper.get("summary", ""),
            "exam_id": paper.get("exam_id"),
            "question_count": len(paper.get("questions", [])),
            "drafts": len(paper.get("drafts", [])),
        }
        prompt = f"试卷已通过审核，请向老师汇报结果（含草稿提示）：{json.dumps(payload, ensure_ascii=False)}"
    elif scope_status == "confirmed" and state.get("exam_paper"):
        payload = {
            "summary": state["exam_paper"].get("summary", ""),
            "exam_id": state["exam_paper"].get("exam_id"),
        }
        prompt = f"考查范围已确认、试卷已装配，请向老师汇报结果：{json.dumps(payload, ensure_ascii=False)}"
    elif tool_result:
        prompt = f"工具执行完毕，请用自然语言向老师汇报结果：{json.dumps(tool_result, ensure_ascii=False)}"
    else:
        prompt = None

    full = messages + ([{"role": "user", "content": prompt}] if prompt else [])
    content = _run(_collect_stream(llm.chat_stream(CHAT_SYSTEM_PROMPT, full)))
    return {"messages": [AIMessage(content=content)]}
