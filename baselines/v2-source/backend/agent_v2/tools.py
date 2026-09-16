"""agent_v2 工具层 — 复用现有服务。

与计划书初稿相比，实际服务的命名与签名如下（此处已对齐）：
- 语义搜题：QuestionService.search_semantic（内部走 RAGPipeline）
- 智能组卷：ExamGenerator.generate（需要 AsyncSession）
- 知识查询：直接查 KnowledgeNode 表（项目中没有独立的 KnowledgeService）

这些函数保持 async，由 nodes.py 中的同步节点通过 asyncio.run() 调用。
"""
from sqlalchemy import select

from app.database import async_session
from app.models.knowledge import KnowledgeNode
from app.services.question_service import QuestionService
from app.services.exam_generator import ExamGenerator


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
    """智能组卷：按题型配比生成试卷，返回题目列表与摘要。"""
    dist = {}
    for n, qtype in (
        (choice_count, "choice"),
        (fill_count, "fill"),
        (tf_count, "tf"),
        (short_answer_count, "short_answer"),
        (code_count, "code"),
    ):
        if n:
            dist[qtype] = n

    requirements = {
        "title": title,
        "knowledge_node_ids": [],
        "question_distribution": dist,
        "difficulty": difficulty,
        "total_score": total_score,
        "duration": duration,
        "scope": scope,
    }

    async with async_session() as db:
        gen = ExamGenerator(db)
        result = await gen.generate(requirements)

    return {
        "requirements": requirements,
        "title": title,
        "total_score": total_score,
        "duration": duration,
        "questions": result.get("questions", []),
        "summary": result.get("summary", ""),
    }
