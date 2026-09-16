"""agent_v2 Graph 编译 — StateGraph + SQLite Checkpoint。

由于运行在 Python 3.10，整条图用「同步节点 + 同步 invoke」编译执行；
Checkpoint 使用同步 SqliteSaver（sqlite3 连接），支持断线续聊与 interrupt 恢复。

主线（ADR-0006）：generate → propose_scope → scope_review(interrupt)
→ assemble → paper_review(interrupt) → chat → END
"""
import sqlite3

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import AgentState
from .nodes import (
    router_node,
    route_after_router,
    search_node,
    generate_node,
    propose_scope_node,
    scope_review_node,
    knowledge_node,
    review_node,
    chat_node,
)

CHECKPOINT_DB = "checkpoints.db"


def compile_app(checkpointer=None):
    """编译 LangGraph 状态机，返回 CompiledStateGraph。"""
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("search", search_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("propose_scope", propose_scope_node)
    workflow.add_node("scope_review", scope_review_node)
    workflow.add_node("knowledge", knowledge_node)
    workflow.add_node("review", review_node)
    workflow.add_node("chat", chat_node)

    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            # key 必须与 router_node 写入 next_action 的 LLM tool name 对齐
            "search_questions": "search",
            "generate_exam": "generate",
            "query_knowledge": "knowledge",
            "chat": "chat",
        },
    )
    workflow.add_edge("search", "chat")
    workflow.add_edge("knowledge", "chat")
    workflow.add_edge("generate", "scope_review")       # 组卷意图 → 先提出范围
    workflow.add_edge("propose_scope", "scope_review")  # 明确提出范围 → 审核
    workflow.add_edge("scope_review", "review")         # 确认后装配并审核试卷
    workflow.add_edge("review", "chat")
    workflow.add_edge("chat", END)

    return workflow.compile(checkpointer=checkpointer)


# 常驻内存的 SQLite 检查点（供测试入口与 chat 路由复用）
_conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
app = compile_app(checkpointer=_checkpointer)
