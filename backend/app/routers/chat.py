"""POST /api/chat — LangGraph 教学助手 SSE 端点（唯一 chat 路径）。

事件：intent / tool_call / scope_pending / review_pending / text / done / error
resume 形状：{"kind": "scope", "confirmed": true, "scope_id"} 或
            {"kind": "paper", "approved": true} 或 {"approved": bool}（兼容 v2）
"""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent_v2.graph import app


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str | None = None      # 用户输入（普通对话）
    thread_id: str = "default"      # 会话线程 ID（Checkpoint 续聊用）
    resume: dict | None = None      # 审核恢复


def _sse(event: str, data) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _updates_to_sse(update: dict) -> list[str]:
    """把一次 stream 更新映射为若干 SSE 帧。"""
    lines = []

    # interrupt：考查范围确认 / 试卷审核
    if "__interrupt__" in update:
        iv = update["__interrupt__"][0].value
        itype = iv.get("type")
        if itype == "scope_review":
            lines.append(_sse("scope_pending", {
                "scope_id": iv.get("scope_id"),
                "tree": iv.get("tree", []),
                "message": iv.get("message"),
            }))
        else:
            lines.append(_sse("review_pending", {
                "exam_paper": iv.get("exam_paper"),
                "message": iv.get("message"),
            }))
        return lines

    for node, val in update.items():
        if node == "router":
            lines.append(_sse("intent", {"next_action": val.get("next_action")}))
        elif node in ("search", "knowledge", "generate", "propose_scope"):
            lines.append(_sse("tool_call", {"tool": node, "result": val.get("tool_result")}))
        elif node == "scope_review":
            lines.append(_sse("scope", {"status": val.get("scope_status")}))
        elif node == "review":
            lines.append(_sse("review", {"status": val.get("review_status")}))
        elif node == "chat":
            msgs = val.get("messages", [])
            if msgs:
                content = getattr(msgs[-1], "content", msgs[-1])
                lines.append(_sse("text", content))
    return lines


@router.post("")
async def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    if req.resume is not None:
        resume = req.resume
        kind = resume.get("kind")
        if kind == "scope":
            # 考查范围确认：确认则带 confirmed，调整则带 adjustments
            payload = {
                "confirmed": bool(resume.get("confirmed")),
                "adjustments": resume.get("adjustments", ""),
            }
        elif kind == "paper":
            payload = {
                "approved": bool(resume.get("approved")),
                "adjustments": resume.get("adjustments", ""),
            }
        else:
            payload = resume
        graph_input = Command(resume=payload)
    else:
        if not req.message:
            graph_input = {"messages": [HumanMessage(content="")]}
        else:
            graph_input = {"messages": [HumanMessage(content=req.message)]}

    def event_stream():
        try:
            for update in app.stream(graph_input, config=config):
                for line in _updates_to_sse(update):
                    yield line
            yield _sse("done", "")
        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
