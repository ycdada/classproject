"""POST /api/chat — SSE streaming AI chat endpoint."""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database import get_db
from ..services.chat_service import ChatService


router = APIRouter(prefix="", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """SSE streaming chat endpoint."""
    service = ChatService(db)

    async def event_stream():
        try:
            async for event in service.process_message(req.message, req.history):
                data = event["data"]
                # text 块可能含换行，会打碎 SSE 帧 — 统一 JSON 编码为单行
                if event["event"] == "text":
                    data = json.dumps(data, ensure_ascii=False)
                yield f"event: {event['event']}\ndata: {data}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
