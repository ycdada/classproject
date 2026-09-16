from datetime import datetime
from pydantic import BaseModel


class MaterialOut(BaseModel):
    id: int
    filename: str
    file_type: str
    chapter: int | None
    content_md: str | None
    page_count: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class MaterialListItem(BaseModel):
    id: int
    filename: str
    file_type: str
    chapter: int | None
    page_count: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}
