"""DraftService — 题目草稿的创建、编辑、接受（入题库）、拒绝。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.draft import QuestionDraft
from ..models.question import Question
from .question_service import QuestionService


class DraftService:
    def __init__(self, db: AsyncSession, question_service: QuestionService | None = None):
        self.db = db
        self._qs = question_service

    async def create_many(self, items: list[dict], exam_scope_id: int | None = None) -> list[QuestionDraft]:
        drafts = []
        for item in items:
            draft = QuestionDraft(
                type=item.get("type", "choice"),
                difficulty=item.get("difficulty", 3),
                chapter=item.get("chapter"),
                knowledge_point_ids=item.get("knowledge_point_ids", []),
                content=item.get("content", ""),
                options=item.get("options"),
                answer=item.get("answer", ""),
                explanation=item.get("explanation"),
                status="pending",
                exam_scope_id=exam_scope_id,
            )
            self.db.add(draft)
            drafts.append(draft)
        await self.db.commit()
        for d in drafts:
            await self.db.refresh(d)
        return drafts

    async def get(self, draft_id: int) -> QuestionDraft | None:
        return await self.db.get(QuestionDraft, draft_id)

    async def list_drafts(self, status: str | None = None) -> list[QuestionDraft]:
        query = select(QuestionDraft).order_by(QuestionDraft.created_at.desc())
        if status:
            query = query.where(QuestionDraft.status == status)
        return list((await self.db.execute(query)).scalars().all())

    async def update(self, draft_id: int, data: dict) -> QuestionDraft:
        """仅 pending 状态可编辑。"""
        draft = await self.get(draft_id)
        if not draft:
            raise ValueError("draft_not_found")
        if draft.status != "pending":
            raise ValueError("draft_not_pending")
        for key, value in data.items():
            if hasattr(draft, key):
                setattr(draft, key, value)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def accept(self, draft_id: int) -> Question:
        """教师确认草稿 → 写入题库（source=manual），并做向量化。"""
        draft = await self.get(draft_id)
        if not draft:
            raise ValueError("draft_not_found")
        if draft.status != "pending":
            raise ValueError("draft_not_pending")

        qs = self._qs or QuestionService(self.db)
        question = await qs.create_question({
            "type": draft.type,
            "difficulty": draft.difficulty,
            "chapter": draft.chapter,
            "knowledge_point_ids": draft.knowledge_point_ids or [],
            "content": draft.content,
            "options": draft.options,
            "answer": draft.answer,
            "explanation": draft.explanation,
            "source": "manual",
        })
        draft.status = "accepted"
        await self.db.commit()
        return question

    async def reject(self, draft_id: int) -> None:
        draft = await self.get(draft_id)
        if not draft:
            raise ValueError("draft_not_found")
        if draft.status != "pending":
            raise ValueError("draft_not_pending")
        draft.status = "rejected"
        await self.db.commit()
