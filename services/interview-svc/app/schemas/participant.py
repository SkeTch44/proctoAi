from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ParticipantRole(str, Enum):
    interviewer = "interviewer"
    interviewee = "interviewee"
    observer = "observer"


class ParticipantResponse(BaseModel):
    id: int
    session_id: str
    user_id: int
    role: str
    display_name: str
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    status: str

    class Config:
        from_attributes = True
