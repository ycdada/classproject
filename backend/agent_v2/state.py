"""agent_v2 状态定义 — LangGraph AgentState。

说明：本项目运行在 Python 3.10 下，LangGraph 的 interrupt() 在异步上下文要求
Python 3.11+，因此整条图采用「同步节点 + 同步 invoke」的方式编译执行，
节点内部再通过 asyncio.run() 调用现有的异步服务（见 nodes.py）。
"""
from typing import Annotated, TypedDict, Optional, Any

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """LangGraph 编排状态。

    messages 使用 add_messages reducer，节点返回的新消息会自动追加到历史。
    """
    messages: Annotated[list, add_messages]   # 对话历史（自动追加）
    next_action: Optional[str]                 # 路由标记：search / generate / knowledge / chat
    tool_args: Optional[dict]                  # 意图识别出的工具调用参数
    tool_result: Optional[dict]                # 工具执行结果
    scope_id: Optional[int]                    # 提出的考查范围 id
    scope_status: Optional[str]                # proposed / confirmed
    scope_tree: Optional[list]                 # 考查范围树（scope_pending 事件数据）
    exam_paper: Optional[dict]                 # 组卷结果（待人工审核）
    review_status: Optional[str]               # pending / approved / rejected / skipped
