import datetime
from sqlalchemy import Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="draft", comment="draft/reviewed/exported")
    total_score: Mapped[int] = mapped_column(Integer, default=100)
    duration: Mapped[int] = mapped_column(Integer, default=120, comment="minutes")
    requirements_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    knowledge_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    questions = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("exams.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=5)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    exam = relationship("Exam", back_populates="questions")
    question = relationship("Question")
