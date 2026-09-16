"""
Exam generation service.
Rule-based selection from question pool + optional LLM generation.
"""
import random
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ..models.exam import Exam, ExamQuestion
from ..models.question import Question
from ..schemas.exam import ExamCreate, ExamGenerateRequest


class ExamService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_exam(self, exam_id: int) -> Exam | None:
        result = await self.db.execute(
            select(Exam)
            .where(Exam.id == exam_id)
            .options(selectinload(Exam.questions).selectinload(ExamQuestion.question))
        )
        exam = result.scalar_one_or_none()
        return exam

    async def list_exams(self, created_by: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        query = select(Exam).options(selectinload(Exam.questions))
        if created_by:
            query = query.where(Exam.created_by == created_by)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Exam.id.desc())
        result = await self.db.execute(query)
        items = result.scalars().unique().all()

        return {"total": total, "items": list(items), "page": page, "page_size": page_size}

    async def create_exam(self, data: ExamCreate) -> Exam:
        exam = Exam(
            title=data.title,
            created_by=data.created_by,
            total_score=data.total_score,
            duration=data.duration,
            status="draft",
        )
        self.db.add(exam)
        await self.db.flush()  # Get exam.id

        # Add questions
        for i, eq_data in enumerate(data.questions):
            eq = ExamQuestion(
                exam_id=exam.id,
                question_id=eq_data.question_id,
                score=eq_data.score,
                sort_order=eq_data.sort_order or i + 1,
            )
            self.db.add(eq)

        await self.db.commit()
        await self.db.refresh(exam, ["questions"])
        return exam

    async def update_exam(self, exam_id: int, data: ExamCreate) -> Exam | None:
        exam = await self.get_exam(exam_id)
        if not exam:
            return None

        exam.title = data.title
        exam.total_score = data.total_score
        exam.duration = data.duration

        # Remove old questions
        for eq in exam.questions:
            await self.db.delete(eq)

        # Add new questions
        for i, eq_data in enumerate(data.questions):
            eq = ExamQuestion(
                exam_id=exam.id,
                question_id=eq_data.question_id,
                score=eq_data.score,
                sort_order=eq_data.sort_order or i + 1,
            )
            self.db.add(eq)

        await self.db.commit()
        await self.db.refresh(exam, ["questions"])
        return exam

    async def delete_exam(self, exam_id: int) -> bool:
        exam = await self.get_exam(exam_id)
        if not exam:
            return False
        await self.db.delete(exam)
        await self.db.commit()
        return True

    async def generate_exam(self, spec: ExamGenerateRequest) -> Exam:
        """Auto-generate an exam from the question pool."""
        questions = []
        type_dist = spec.type_distribution
        diff_dist = spec.difficulty_distribution
        count = spec.question_count

        # Calculate per-type count
        type_counts = {}
        for qtype, pct in type_dist.items():
            n = max(1, int(count * pct / 100))
            type_counts[qtype] = n

        # Adjust to match exactly count
        total = sum(type_counts.values())
        if total != count:
            diff = count - total
            # Add/remove from the largest type
            largest_type = max(type_counts, key=type_counts.get)
            type_counts[largest_type] += diff

        # Calculate per-difficulty distribution
        difficulty_weights = []
        for d, pct in diff_dist.items():
            difficulty_weights.extend([d] * pct)

        used_ids = set()
        for qtype, type_count in type_counts.items():
            for i in range(type_count):
                # Pick difficulty based on distribution
                target_diff = random.choice(difficulty_weights) if difficulty_weights else 3

                # Query for matching questions
                query = select(Question).where(
                    Question.type == qtype,
                    Question.id.notin_(used_ids) if used_ids else True,
                ).order_by(func.abs(Question.difficulty - target_diff))

                result = await self.db.execute(query.limit(10))
                candidates = result.scalars().all()

                if candidates:
                    q = candidates[0]
                    used_ids.add(q.id)
                    questions.append({"question": q, "difficulty_weights": difficulty_weights})

        # Create exam
        exam = Exam(
            title=spec.title,
            created_by=spec.created_by,
            total_score=spec.total_score,
            duration=spec.duration,
            status="ready",
        )
        self.db.add(exam)
        await self.db.flush()

        # Assign default scores (evenly distribute)
        per_question_score = spec.total_score // max(len(questions), 1)
        remainder = spec.total_score - per_question_score * len(questions)

        for i, item in enumerate(questions):
            score = per_question_score + (1 if i < remainder else 0)
            eq = ExamQuestion(
                exam_id=exam.id,
                question_id=item["question"].id,
                score=score,
                sort_order=i + 1,
            )
            self.db.add(eq)

        await self.db.commit()
        await self.db.refresh(exam, ["questions"])
        return exam
