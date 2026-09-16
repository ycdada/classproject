"""PaperAssembler — 组卷唯一实现：确认的考查范围 + 题库检索 + 缺口写草稿。"""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.question import Question
from ..models.scope import ExamScope, ExamScopeNode
from .draft_service import DraftService
from .question_author import draft_from_author_item


def normalize_scores(questions: list[dict], total_score: int) -> list[dict]:
    """Ensure sum of question scores exactly equals total_score."""
    count = len(questions)
    if count == 0:
        return questions
    base = total_score // count
    remainder = total_score - base * count
    for i, q in enumerate(questions):
        q["score"] = base + (1 if i < remainder else 0)
    return questions


@dataclass
class AssembleResult:
    questions: list[dict] = field(default_factory=list)
    drafts: list[dict] = field(default_factory=list)
    shortfall: dict[str, int] = field(default_factory=dict)
    summary: str = ""


class QuestionAuthor:
    async def propose(self, spec: dict, context: str) -> list[dict]:
        raise NotImplementedError


class FakeRag:
    """测试缝：search 返回预置题目 id 列表。"""

    def __init__(self, ids: list[int]):
        self.ids = ids

    def search(self, query_embedding, top_k: int = 20, where: dict | None = None):
        return [{"id": i, "metadata": {}, "distance": 0.1, "document": ""} for i in self.ids[:top_k]]


class PaperAssembler:
    def __init__(self, db: AsyncSession, rag, llm, author, drafts: DraftService):
        self.db = db
        self.rag = rag
        self.llm = llm
        self.author = author
        self.drafts = drafts

    async def assemble(self, demand: dict, scope: ExamScope) -> AssembleResult:
        if scope.status != "confirmed":
            raise ValueError("scope_not_confirmed")

        scope_nodes = (await self.db.execute(
            select(ExamScopeNode)
            .where(ExamScopeNode.scope_id == scope.id, ExamScopeNode.included == True)  # noqa: E712
        )).scalars().all()
        context = self._build_context(scope_nodes)

        dist = demand.get("question_distribution") or {}
        questions: list[dict] = []
        drafts_out: list[dict] = []
        shortfall: dict[str, int] = {}
        used_ids: set[int] = set()

        for qtype, count in dist.items():
            count = int(count)
            if count <= 0:
                continue
            picked = await self._pick_from_bank(qtype, context, count, used_ids)
            for q in picked:
                used_ids.add(q["question_id"])
            questions.extend(picked)

            missing = count - len(picked)
            if missing > 0:
                shortfall[qtype] = missing
                spec = {
                    "type": qtype,
                    "count": missing,
                    "difficulty": self._avg_difficulty(demand),
                }
                proposed = []
                if self.author is not None:
                    try:
                        proposed = await self.author.propose(spec, context)
                    except Exception as e:
                        print(f"[PaperAssembler] author.propose failed: {e}")
                draft_items = [draft_from_author_item(it, spec) for it in proposed[:missing]]
                created = await self.drafts.create_many(
                    draft_items, exam_scope_id=scope.id
                )
                for d in created:
                    drafts_out.append({
                        "id": d.id,
                        "type": d.type,
                        "content": d.content,
                        "status": d.status,
                    })

        questions = normalize_scores(questions, int(demand.get("total_score", 100)))
        for i, q in enumerate(questions):
            q["sort_order"] = i

        if not questions and not drafts_out:
            raise ValueError("no_questions_and_no_drafts")

        summary = self._build_summary(demand, questions, shortfall)
        return AssembleResult(
            questions=questions,
            drafts=drafts_out,
            shortfall=shortfall,
            summary=summary,
        )

    async def _pick_from_bank(self, qtype: str, context: str, count: int,
                              used_ids: set[int]) -> list[dict]:
        if not context:
            return []
        embedding = None
        if self.llm is not None:
            try:
                embedding = await self.llm.embed(context[:500])
            except Exception as e:
                print(f"[PaperAssembler] embed failed: {e}")
                embedding = None
        results = self.rag.search(embedding or [0.0], top_k=max(count * 5, count), where={"type": qtype})

        ids = [r["id"] for r in results if r["id"] not in used_ids]
        if not ids:
            return []
        rows = (await self.db.execute(
            select(Question).where(Question.id.in_(ids))
        )).scalars().all()
        row_map = {r.id: r for r in rows}

        picked = []
        for r in results:
            if len(picked) >= count:
                break
            q = row_map.get(r["id"])
            if not q or q.id in used_ids:
                continue
            picked.append({
                "question_id": q.id,
                "type": q.type,
                "difficulty": q.difficulty,
                "chapter": q.chapter,
                "content": q.content,
                "options": q.options,
                "answer": q.answer,
                "explanation": q.explanation,
                "knowledge_point_ids": q.knowledge_point_ids,
                "score": 1,
                "sort_order": 0,
            })
        return picked

    def _build_context(self, scope_nodes: list[ExamScopeNode]) -> str:
        parts = []
        for n in scope_nodes:
            if n.node_type == "point":
                block = [f"## {n.name}"]
                if n.definition:
                    block.append(f"定义: {n.definition}")
                if n.key_terms:
                    block.append("术语: " + ", ".join(n.key_terms))
                if n.solution_steps:
                    block.append(f"解题步骤: {n.solution_steps}")
                if n.teaching_emphasis:
                    block.append(f"教学重点: {n.teaching_emphasis}")
                parts.append("\n".join(block))
            else:
                parts.append(f"# {n.name}")
        return "\n\n".join(parts)

    @staticmethod
    def _avg_difficulty(demand: dict) -> int:
        dd = demand.get("difficulty_distribution") or {}
        try:
            total = sum(int(v) for v in dd.values())
            if total <= 0:
                return 3
            weighted = sum(int(k) * int(v) for k, v in dd.items())
            return max(1, min(5, round(weighted / total)))
        except (ValueError, TypeError):
            return 3

    @staticmethod
    def _build_summary(demand: dict, questions: list[dict], shortfall: dict) -> str:
        title = demand.get("title", "试卷")
        total = len(questions)
        if shortfall:
            miss = ", ".join(f"{k}缺{n}道" for k, n in shortfall.items())
            return f"《{title}》：从题库装配 {total} 道题；{miss}，缺口已写入题目草稿，请到草稿页确认。"
        return f"《{title}》：从题库装配 {total} 道题，满足题型要求。"
