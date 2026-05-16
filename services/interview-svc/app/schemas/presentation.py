from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PresentationResponse(BaseModel):
    id: str
    session_id: str
    filename: str
    file_url: str
    slide_count: int
    current_slide: int
    slides_json: Optional[str] = None
    uploaded_by: int
    uploaded_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class SlideChangeRequest(BaseModel):
    slide_index: int = Field(..., ge=0)


class UploadResponse(BaseModel):
    id: str
    session_id: str
    filename: str
    slide_count: int
    current_slide: int
    is_active: bool
