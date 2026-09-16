"""POST /api/v2/chat — LangGraph v2 SSE 端点。

与 v1 并行共存，不影响原 /api/chat。同步图经 StreamingResponse 的线程池执行，
节点内部再通过 asyncio.run() 调用异步服务。
"""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent_v2.graph import app


router = APIRouter(prefix="/v2/chat", tags=["v2"])


class ChatV2Request(BaseModel):
    message: str | None = None      # 用户输入（普通对话）
    thread_id: str = "default"      # 会话线程 ID（Checkpoint 续聊用）
    resume: dict | None = None      # 审核恢复：{"approved": bool, "adjustments": str}


def _sse(event: str, data) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _updates_to_sse(update: dict) -> list[str]:
    """把一次 stream 更新映射为若干 SSE 帧。"""
    lines = []

    # interrupt：组卷后暂停，等待人工审核
    if "__interrupt__" in update:
        iv = update["__interrupt__"][0].value
        lines.append(_sse("review_pending", {
            "exam_paper": iv.get("exam_paper"),
            "message": iv.get("message"),
        }))
        return lines

    for node, val in update.items():
        if node == "router":
            lines.append(_sse("intent", {"next_action": val.get("next_action")}))
        elif node in ("search", "knowledge", "generate"):
            lines.append(_sse("tool_call", {"tool": node, "result": val.get("tool_result")}))
        elif node == "review":
            lines.append(_sse("review", {"status": val.get("review_status")}))
        elif node == "chat":
            msgs = val.get("messages", [])
            if msgs:
                content = getattr(msgs[-1], "content", msgs[-1])
                lines.append(_sse("text", content))
    return lines


@router.post("")
async def chat_v2(req: ChatV2Request):
    config = {"configurable": {"thread_id": req.thread_id}}

    if req.resume is not None:
        graph_input = Command(resume=req.resume)
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
