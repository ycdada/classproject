"""PaperAssembler 测试：未确认范围拒绝；缺口写草稿且题库不动。"""
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models.question import Question
from app.models.scope import ExamScope, ExamScopeNode
from app.services.draft_service import DraftService
from app.services.paper_assembler import PaperAssembler


class FakeRag:
    def __init__(self, ids):
        self.ids = ids

    def search(self, query_embedding, top_k=20, where=None):
        return [{"id": i, "metadata": {}, "distance": 0.1, "document": ""} for i in self.ids[:top_k]]


class FakeAuthor:
    async def propose(self, spec, context):
        n = spec["count"]
        return [{"type": spec["type"], "difficulty": 3, "chapter": "", "knowledge_point_ids": [],
                 "content": f"草稿{i}", "options": {"A": "1", "B": "2", "C": "3", "D": "4"} if spec["type"] == "choice" else None,
                 "answer": "A" if spec["type"] == "choice" else "略", "explanation": ""} for i in range(n)]


@pytest.fixture
async def db(monkeypatch):
    import app.services.question_service as qsm

    class FakeLLM:
        async def embed(self, text):
            return [0.0] * 8

    monkeypatch.setattr(qsm, "RAGPipeline", lambda: FakeRag([]))
    monkeypatch.setattr(qsm, "LLMAdapter", lambda: FakeLLM())

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


async def make_confirmed_scope(db) -> ExamScope:
    scope = ExamScope(status="proposed", demand_json={})
    db.add(scope)
    await db.flush()
    db.add(ExamScopeNode(
        scope_id=scope.id, parent_id=None, sort_order=0,
        name="第5章 树和二叉树", node_type="chapter", included=True,
    ))
    await db.flush()
    db.add(ExamScopeNode(
        scope_id=scope.id, parent_id=None, sort_order=1,
        name="先序遍历", node_type="point", definition="根左右",
        key_terms=["先序"], teaching_emphasis="递归",
        solution_steps="访根→左→右", included=True,
    ))
    scope.status = "confirmed"
    await db.commit()
    await db.refresh(scope)
    return scope


def make_demand():
    return {
        "title": "单元测验",
        "duration": 60,
        "total_score": 10,
        "teaching_progress": "已讲完树",
        "exam_scope": "二叉树遍历",
        "focus_notes": "先序遍历",
        "material_ids": [],
        "question_distribution": {"choice": 3},
        "difficulty_distribution": {"3": 100},
    }


@pytest.mark.asyncio
async def test_shortfall_creates_drafts_not_questions(db):
    existing = Question(type="choice", difficulty=3, content="已有选择题", answer="A", source="manual")
    db.add(existing)
    await db.commit()
    scope = await make_confirmed_scope(db)
    demand = make_demand()

    before = (await db.execute(select(func.count(Question.id)))).scalar()
    result = await PaperAssembler(db, rag=FakeRag([existing.id]), llm=None, author=FakeAuthor(), drafts=DraftService(db)).assemble(demand, scope)
    after = (await db.execute(select(func.count(Question.id)))).scalar()

    assert after == before
    assert len(result.questions) == 1
    assert result.questions[0]["question_id"] == existing.id
    assert len(result.drafts) == 2
    assert result.shortfall["choice"] == 2


@pytest.mark.asyncio
async def test_assemble_rejects_unconfirmed_scope(db):
    scope = ExamScope(status="proposed", demand_json={})
    db.add(scope)
    await db.commit()
    demand = make_demand()
    with pytest.raises(ValueError, match="scope_not_confirmed"):
        await PaperAssembler(db, rag=FakeRag([]), llm=None, author=FakeAuthor(), drafts=DraftService(db)).assemble(demand, scope)


@pytest.mark.asyncio
async def test_bank_only_when_enough(db):
    q1 = Question(type="choice", difficulty=3, content="选择题1", answer="A", source="manual")
    q2 = Question(type="choice", difficulty=3, content="选择题2", answer="B", source="manual")
    q3 = Question(type="choice", difficulty=3, content="选择题3", answer="C", source="manual")
    db.add_all([q1, q2, q3])
    await db.commit()
    scope = await make_confirmed_scope(db)
    demand = make_demand()

    result = await PaperAssembler(db, rag=FakeRag([q1.id, q2.id, q3.id]), llm=None, author=FakeAuthor(), drafts=DraftService(db)).assemble(demand, scope)
    assert len(result.questions) == 3
    assert result.drafts == []
    assert result.shortfall == {}
    assert sum(q["score"] for q in result.questions) == 10
