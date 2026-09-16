import datetime
from sqlalchemy import Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class QuestionDraft(Base):
    __tablename__ = "question_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="choice/fill/tf/short_answer/code")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="1-5")
    chapter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    knowledge_point_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending",
                                        comment="pending/accepted/rejected")
    exam_scope_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("exam_scopes.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
