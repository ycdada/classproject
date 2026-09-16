from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class QuestionCreate(BaseModel):
    type: str = Field(..., pattern="^(choice|fill|tf|short_answer|code)$")
    difficulty: int = Field(..., ge=1, le=5)
    knowledge_point_ids: list[str] = Field(default_factory=list)
    chapter: str | None = None
    content: str
    options: dict | None = None
    answer: str
    explanation: str | None = None
    source: str = "manual"


class QuestionUpdate(BaseModel):
    type: str | None = Field(None, pattern="^(choice|fill|tf|short_answer|code)$")
    difficulty: int | None = Field(None, ge=1, le=5)
    knowledge_point_ids: list[str] | None = None
    chapter: str | None = None
    content: str | None = None
    options: dict | None = None
    answer: str | None = None
    explanation: str | None = None
    source: str | None = None


class QuestionOut(BaseModel):
    id: int
    type: str
    difficulty: int
    chapter: str | None = None
    knowledge_point_ids: list[str]
    content: str
    options: dict | None = None
    answer: str
    explanation: str | None = None
    source: str
    embedding_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionFilter(BaseModel):
    type: str | None = None
    difficulty: int | None = None
    knowledge_point: str | None = None
    source: str | None = None
    chapter: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class QuestionListOut(BaseModel):
    total: int
    items: list[QuestionOut]
    page: int
    page_size: int


class SeedQuestionCreate(BaseModel):
    type: str
    difficulty: int
    knowledge_point_ids: list[int] = []
    chapter: str | None = None
    content: str
    options: dict | None = None
    answer: str
    explanation: str | None = None
    source: str = "manual"
    material_id: int | None = None
