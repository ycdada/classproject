from pydantic import BaseModel


class KnowledgeNodeUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    definition: str | None = None
    key_terms: list[str] | None = None
    teaching_emphasis: str | None = None


class KnowledgeNodeOut(BaseModel):
    id: int
    material_id: int
    parent_id: int | None
    sort_order: int
    name: str
    node_type: str
    definition: str | None
    key_terms: list | None
    teaching_emphasis: str | None
    children: list["KnowledgeNodeOut"] = []

    model_config = {"from_attributes": True}
