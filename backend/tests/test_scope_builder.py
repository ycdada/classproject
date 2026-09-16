import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models.material import Material
from app.models.knowledge import KnowledgeNode
from app.services.scope_builder import ScopeBuilder


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_propose_keeps_matching_chapter_only(db):
    m = Material(filename="ch5.pptx", file_type="pptx", file_path="x", kind="slides")
    db.add(m)
    await db.flush()
    ch = KnowledgeNode(material_id=m.id, parent_id=None, name="第5章 树和二叉树", node_type="chapter", sort_order=0)
    db.add(ch)
    await db.flush()
    pt = KnowledgeNode(material_id=m.id, parent_id=ch.id, name="先序遍历", node_type="point",
                       definition="根左右", teaching_emphasis="递归", solution_steps="访根→左→右", sort_order=0)
    other = KnowledgeNode(material_id=m.id, parent_id=None, name="第8章 排序", node_type="chapter", sort_order=1)
    db.add_all([pt, other])
    await db.commit()
    scope = await ScopeBuilder(db).propose({
        "title": "单元测验",
        "teaching_progress": "已讲完树",
        "exam_scope": "二叉树遍历",
        "focus_notes": "先序遍历",
        "material_ids": [m.id],
        "question_distribution": {"choice": 2},
        "difficulty_distribution": {"3": 100},
        "duration": 60,
        "total_score": 10,
    })
    from app.models.scope import ExamScopeNode
    names = {n.name for n in (await db.execute(select(ExamScopeNode).where(ExamScopeNode.scope_id == scope.id))).scalars()}
    assert "先序遍历" in names
    assert "第8章 排序" not in names
    assert scope.status == "proposed"
