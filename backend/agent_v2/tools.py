"""agent_v2 工具层 — 复用现有服务。

- 语义搜题：QuestionService.search_semantic（内部走 RAGPipeline）
- 知识查询：直接查 KnowledgeNode 表
- 组卷：agent_v2.nodes.propose_scope_node 先提出考查范围，确认后由
  PaperAssembler.assemble 装配（缺题只写题目草稿，不写题库）

这些函数保持 async，由 nodes.py 中的同步节点通过 asyncio.run() 调用。
"""
from sqlalchemy import select

from app.database import async_session
from app.models.knowledge import KnowledgeNode
from app.services.question_service import QuestionService
from app.services.scope_builder import ScopeBuilder
from app.services.paper_assembler import PaperAssembler
from app.services.draft_service import DraftService


async def propose_scope(demand: dict) -> dict:
    """提出考查范围：从出卷需求过滤课程知识树，返回 proposed 范围树。"""
    async with async_session() as db:
        scope = await ScopeBuilder(db).propose(demand)
        from app.models.scope import ExamScopeNode
        nodes = (await db.execute(
            select(ExamScopeNode).where(ExamScopeNode.scope_id == scope.id)
        )).scalars().all()

        def build(parent_id):
            out = []
            for n in sorted((x for x in nodes if x.parent_id == parent_id), key=lambda x: x.sort_order):
                out.append({
                    "id": n.id, "name": n.name, "node_type": n.node_type,
                    "definition": n.definition, "key_terms": n.key_terms,
                    "teaching_emphasis": n.teaching_emphasis,
                    "solution_steps": n.solution_steps,
                    "included": n.included, "children": build(n.id),
                })
            return out

        return {"scope_id": scope.id, "status": scope.status, "tree": build(None)}


async def assemble_paper(demand: dict, scope_id: int) -> dict:
    """按确认后的考查范围组卷。未确认抛 ValueError('scope_not_confirmed')。"""
    from app.models.scope import ExamScope

    async with async_session() as db:
        scope = await db.get(ExamScope, scope_id)
        if not scope:
            raise ValueError("scope_not_found")
        assembler = PaperAssembler(db, rag=None, llm=None, author=None, drafts=DraftService(db))
        result = await assembler.assemble_with_rag(demand, scope)
        exam = None
        if result.questions:
            from app.models.exam import Exam, ExamQuestion
            from app.services.paper_assembler import normalize_scores
            exam = Exam(
                title=demand.get("title", "未命名试卷"),
                created_by="teacher",
                total_score=demand.get("total_score", 100),
                duration=demand.get("duration", 120),
                requirements_json=demand,
                knowledge_snapshot_json=result.scope_snapshot,
                status="draft",
            )
            db.add(exam)
            await db.flush()
            for idx, q in enumerate(result.questions):
                db.add(ExamQuestion(
                    exam_id=exam.id, question_id=q["question_id"],
                    score=q["score"], sort_order=idx,
                ))
            await db.commit()
            await db.refresh(exam)
        return {
            "exam_id": exam.id if exam else None,
            "questions": result.questions,
            "drafts": result.drafts,
            "shortfall": result.shortfall,
            "summary": result.summary,
        }


async def search_questions(query: str, type: str | None = None,
                           difficulty: int | None = None,
                           count: int = 10) -> dict:
    """语义搜题：根据关键词 / 知识点在题库中检索。"""
    async with async_session() as db:
        service = QuestionService(db)
        where = {}
        if type:
            where["type"] = type
        if difficulty:
            where["difficulty"] = difficulty
        results = await service.search_semantic(query, top_k=count, where=where or None)

    items = []
    for r in results:
        q = r.get("question") or {}
        items.append({
            "id": q.get("id"),
            "type": q.get("type"),
            "difficulty": q.get("difficulty"),
            "chapter": q.get("chapter"),
            "content": q.get("content"),
        })
    return {"query": query, "count": len(items), "results": items}


async def query_knowledge(topic: str) -> dict:
    """知识查询：按知识点名称模糊检索知识树节点。"""
    async with async_session() as db:
        result = await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.name.contains(topic))
        )
        nodes = result.scalars().all()

    return {
        "topic": topic,
        "results": [
            {
                "name": n.name,
                "definition": n.definition,
                "key_terms": n.key_terms,
                "teaching_emphasis": n.teaching_emphasis,
            }
            for n in nodes[:5]
        ],
    }


async def generate_exam(title: str, scope: str, choice_count: int = 10,
                        fill_count: int = 5, tf_count: int = 5,
                        short_answer_count: int = 3, code_count: int = 2,
                        difficulty: int = 3, total_score: int = 100,
                        duration: int = 120) -> dict:
    """组卷意图入口（v3）：先提出考查范围供教师确认，不直接生成试卷。"""
    demand = {
        "title": title,
        "teaching_progress": "",
        "exam_scope": scope,
        "focus_notes": "",
        "material_ids": [],
        "question_distribution": {},
        "difficulty_distribution": {},
        "total_score": total_score,
        "duration": duration,
    }
    return await propose_scope(demand)
