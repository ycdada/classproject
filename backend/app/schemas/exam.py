from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExamQuestionItem(BaseModel):
    question_id: int
    score: int = 5
    sort_order: int = 0


class ExamCreate(BaseModel):
    title: str
    created_by: str
    total_score: int = 100
    duration: int = 120
    questions: list[ExamQuestionItem] = Field(default_factory=list)


class ExamGenerateRequest(BaseModel):
    title: str
    created_by: str
    total_score: int = 100
    duration: int = 120
    difficulty_distribution: dict[int, int] = Field(
        default_factory=lambda: {1: 10, 2: 20, 3: 40, 4: 20, 5: 10},
        description="Difficulty 1-5 → percentage"
    )
    type_distribution: dict[str, int] = Field(
        default_factory=lambda: {"choice": 40, "fill": 20, "tf": 10, "short_answer": 20, "code": 10},
        description="Question type → percentage"
    )
    knowledge_points: list[str] = Field(default_factory=list)
    question_count: int = Field(default=20, ge=1, le=100)


class ExamOut(BaseModel):
    id: int
    title: str
    created_by: str
    status: str
    total_score: int
    duration: int
    created_at: datetime
    questions: list[ExamQuestionItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ExamListOut(BaseModel):
    total: int
    items: list[ExamOut]
    page: int
    page_size: int


class ExamRequirements(BaseModel):
    title: str
    duration: int = 120
    total_score: int = 100
    teaching_progress: str = ""
    exam_scope: str = ""
    focus_notes: str = ""
    material_ids: list[int] = Field(default_factory=list)
    knowledge_node_ids: list[int] = Field(default_factory=list)  # 仅作备用；考查范围确认后以 scope 为准
    scope_id: int | None = None  # 确认后的考查范围 id；组卷必填
    question_distribution: dict = Field(default_factory=dict)  # {"choice": 10, "fill": 5, ...}
    difficulty_distribution: dict = Field(default_factory=dict)  # {"1": 10, "2": 30, ...}
