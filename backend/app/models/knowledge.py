import datetime
from sqlalchemy import Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("materials.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("knowledge_nodes.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="chapter/section/point")
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_terms: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    teaching_emphasis: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
