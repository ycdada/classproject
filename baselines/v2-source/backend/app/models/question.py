import datetime
from sqlalchemy import Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="choice/fill/tf/short_answer/code")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-5")
    chapter: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="所属章节，如'第3章 栈和队列'")
    knowledge_point_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", comment="ppt_extracted/manual")
    material_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("materials.id"), nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="ChromaDB vector ID")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
