"""DraftService 测试：accept 使 questions 表 +1 且 draft.status=accepted；reject 不增加。"""
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models.draft import QuestionDraft
from app.models.question import Question
from app.services.draft_service import DraftService

DRAFT_ITEM = {
    "type": "choice",
    "difficulty": 3,
    "chapter": "第5章 树和二叉树",
    "knowledge_point_ids": [],
    "content": "先序遍历的顺序是？",
    "options": {"A": "根左右", "B": "左根右", "C": "左右根", "D": "根右左"},
    "answer": "A",
    "explanation": "",
}


@pytest.fixture
async def db(monkeypatch):
    # 环境无 DeepSeek key，FakeLLM 兜底，避免 AsyncOpenAI 构造报错
    import app.services.question_service as qsm
    monkeypatch.setattr(qsm, "RAGPipeline", lambda: FakeRag())
    monkeypatch.setattr(qsm, "LLMAdapter", lambda: FakeLLM())
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


class FakeRag:
    def add_question(self, question_id, content, embedding, metadata):
        return str(question_id)


class FakeLLM:
    async def embed(self, text):
        return [0.0] * 8


@pytest.mark.asyncio
async def test_accept_moves_draft_into_question_bank(db):
    drafts = await DraftService(db).create_many([DRAFT_ITEM])
    assert len(drafts) == 1
    assert drafts[0].status == "pending"

    before = (await db.execute(select(func.count(Question.id)))).scalar()
    question = await DraftService(db).accept(drafts[0].id)
    after = (await db.execute(select(func.count(Question.id)))).scalar()

    assert after == before + 1
    assert question.source == "manual"
    draft = await DraftService(db).get(drafts[0].id)
    assert draft.status == "accepted"


@pytest.mark.asyncio
async def test_reject_leaves_bank_unchanged(db):
    drafts = await DraftService(db).create_many([DRAFT_ITEM])
    before = (await db.execute(select(func.count(Question.id)))).scalar()
    await DraftService(db).reject(drafts[0].id)
    after = (await db.execute(select(func.count(Question.id)))).scalar()
    assert after == before
    draft = await DraftService(db).get(drafts[0].id)
    assert draft.status == "rejected"


@pytest.mark.asyncio
async def test_accepted_draft_cannot_be_edited(db):
    drafts = await DraftService(db).create_many([DRAFT_ITEM])
    svc = DraftService(db)
    await svc.accept(drafts[0].id)
    with pytest.raises(ValueError, match="draft_not_pending"):
        await svc.update(drafts[0].id, {"content": "改不动"})
