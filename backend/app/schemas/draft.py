from datetime import datetime
from pydantic import BaseModel


class QuestionDraftOut(BaseModel):
    id: int
    type: str
    difficulty: int
    chapter: str | None
    knowledge_point_ids: list
    content: str
    options: dict | None
    answer: str
    explanation: str | None
    status: str
    exam_scope_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionDraftUpdate(BaseModel):
    type: str | None = None
    difficulty: int | None = None
    chapter: str | None = None
    knowledge_point_ids: list | None = None
    content: str | None = None
    options: dict | None = None
    answer: str | None = None
    explanation: str | None = None
