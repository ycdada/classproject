"""题目草稿 HTTP：列表、编辑、接受、拒绝。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas.draft import QuestionDraftOut, QuestionDraftUpdate
from ..services.draft_service import DraftService

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get("", response_model=list[QuestionDraftOut])
async def list_drafts(status: str | None = None, db: AsyncSession = Depends(get_db)):
    return await DraftService(db).list_drafts(status)


@router.put("/{draft_id}", response_model=QuestionDraftOut)
async def update_draft(draft_id: int, data: QuestionDraftUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await DraftService(db).update(draft_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        msg = str(e)
        if msg == "draft_not_found":
            raise HTTPException(404, "Draft not found")
        raise HTTPException(409, "Draft is not pending")


@router.post("/{draft_id}/accept", response_model=dict)
async def accept_draft(draft_id: int, db: AsyncSession = Depends(get_db)):
    try:
        question = await DraftService(db).accept(draft_id)
    except ValueError as e:
        msg = str(e)
        if msg == "draft_not_found":
            raise HTTPException(404, "Draft not found")
        raise HTTPException(409, "Draft is not pending")
    return {"status": "ok", "question_id": question.id}


@router.post("/{draft_id}/reject", response_model=QuestionDraftOut)
async def reject_draft(draft_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await DraftService(db).reject(draft_id)
    except ValueError as e:
        msg = str(e)
        if msg == "draft_not_found":
            raise HTTPException(404, "Draft not found")
        raise HTTPException(409, "Draft is not pending")
    draft = await DraftService(db).get(draft_id)
    return draft
