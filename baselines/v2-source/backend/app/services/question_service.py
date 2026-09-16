"""Question service — CRUD with ChromaDB sync."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.question import Question
from .llm_adapter import LLMAdapter
from .rag import RAGPipeline


class QuestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.rag = RAGPipeline()

    async def list_questions(self, page: int = 1, page_size: int = 20,
                             qtype: str | None = None, difficulty: int | None = None,
                             chapter: str | None = None, keyword: str | None = None
                             ) -> tuple[list[Question], int]:
        query = select(Question)
        count_query = select(func.count(Question.id))

        if qtype:
            query = query.where(Question.type == qtype)
            count_query = count_query.where(Question.type == qtype)
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
            count_query = count_query.where(Question.difficulty == difficulty)
        if chapter:
            query = query.where(Question.chapter == chapter)
            count_query = count_query.where(Question.chapter == chapter)
        if keyword:
            query = query.where(Question.content.contains(keyword))
            count_query = count_query.where(Question.content.contains(keyword))

        total = (await self.db.execute(count_query)).scalar()
        questions = (await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()

        return questions, total

    async def get_question(self, question_id: int) -> Question | None:
        result = await self.db.execute(
            select(Question).where(Question.id == question_id)
        )
        return result.scalar_one_or_none()

    async def create_question(self, data: dict) -> Question:
        question = Question(**data)
        self.db.add(question)
        await self.db.flush()

        # Vectorize and store
        text_for_embedding = self._build_embed_text(question)
        embedding = await self.llm.embed(text_for_embedding)
        metadata = {
            "type": question.type,
            "difficulty": question.difficulty,
            "chapter": question.chapter or "",
            "knowledge_points": ",".join(question.knowledge_point_ids or []),
        }
        eid = self.rag.add_question(question.id, text_for_embedding, embedding, metadata)
        question.embedding_id = eid
        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def update_question(self, question_id: int, data: dict) -> Question | None:
        question = await self.get_question(question_id)
        if not question:
            return None
        for key, value in data.items():
            if hasattr(question, key):
                setattr(question, key, value)

        # Re-vectorize
        text_for_embedding = self._build_embed_text(question)
        embedding = await self.llm.embed(text_for_embedding)
        metadata = {
            "type": question.type,
            "difficulty": question.difficulty,
            "chapter": question.chapter or "",
            "knowledge_points": ",".join(question.knowledge_point_ids or []),
        }
        self.rag.add_question(question.id, text_for_embedding, embedding, metadata)

        await self.db.commit()
        await self.db.refresh(question)
        return question

    async def delete_question(self, question_id: int) -> bool:
        question = await self.get_question(question_id)
        if not question:
            return False
        self.rag.delete_question(question_id)
        await self.db.delete(question)
        await self.db.commit()
        return True

    async def search_semantic(self, query: str, top_k: int = 20,
                              where: dict | None = None) -> list[dict]:
        """RAG semantic search."""
        query_embedding = await self.llm.embed(query)
        results = self.rag.search(query_embedding, top_k=top_k, where=where)

        # Load full question data from DB
        ids = [r["id"] for r in results]
        if ids:
            rows = (await self.db.execute(
                select(Question).where(Question.id.in_(ids))
            )).scalars().all()
            row_map = {r.id: r for r in rows}
            for r in results:
                q = row_map.get(r["id"])
                if q:
                    r["question"] = {
                        "id": q.id, "type": q.type, "difficulty": q.difficulty,
                        "chapter": q.chapter, "content": q.content,
                        "options": q.options, "answer": q.answer,
                        "explanation": q.explanation, "knowledge_points": q.knowledge_point_ids,
                    }
        return results

    async def embed_all(self) -> int:
        """Re-embed all questions in the database."""
        self.rag.reset()
        result = await self.db.execute(select(Question))
        questions = result.scalars().all()

        batch = []
        for q in questions:
            text = self._build_embed_text(q)
            embedding = await self.llm.embed(text)
            batch.append({
                "id": q.id,
                "content": text,
                "embedding": embedding,
                "metadata": {
                    "type": q.type,
                    "difficulty": q.difficulty,
                    "chapter": q.chapter or "",
                    "knowledge_points": ",".join(q.knowledge_point_ids or []),
                },
            })
            q.embedding_id = str(q.id)

        self.rag.add_questions_batch(batch)
        await self.db.commit()
        return len(questions)

    def _build_embed_text(self, q: Question) -> str:
        """Build a text representation of a question for embedding."""
        parts = [q.content]
        if q.options:
            parts.append(" ".join(f"{k}. {v}" for k, v in q.options.items()))
        if q.knowledge_point_ids:
            parts.append("知识点: " + ", ".join(q.knowledge_point_ids))
        if q.chapter:
            parts.append(f"章节: {q.chapter}")
        return " | ".join(parts)
