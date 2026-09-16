from pydantic import BaseModel


class ExamScopeNodeOut(BaseModel):
    id: int
    scope_id: int
    parent_id: int | None
    source_node_id: int | None
    sort_order: int
    name: str
    node_type: str
    definition: str | None
    key_terms: list | None
    teaching_emphasis: str | None
    solution_steps: str | None
    included: bool
    children: list["ExamScopeNodeOut"] = []

    model_config = {"from_attributes": True}


class ExamScopeOut(BaseModel):
    id: int
    status: str
    demand_json: dict | None
    tree: list[ExamScopeNodeOut] = []

    model_config = {"from_attributes": True}


class ExamScopeNodeUpdate(BaseModel):
    name: str | None = None
    definition: str | None = None
    key_terms: list[str] | None = None
    teaching_emphasis: str | None = None
    solution_steps: str | None = None
    included: bool | None = None


class ExamScopeNodeCreate(BaseModel):
    parent_id: int | None = None
    name: str
    node_type: str = "point"
    definition: str | None = None
    key_terms: list[str] | None = None
    teaching_emphasis: str | None = None
    solution_steps: str | None = None
    included: bool = True
