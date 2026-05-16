from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.participant import ParticipantResponse


class CreateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    max_participants: int = Field(default=6, ge=2, le=10)
    scheduled_at: Optional[datetime] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    room_name: str
    creator_id: int
    status: str
    max_participants: int
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JoinSessionRequest(BaseModel):
    role: str = Field(..., pattern=r"^(interviewer|interviewee|observer)$")
    display_name: str = Field(..., min_length=1, max_length=200)


class JoinSessionResponse(BaseModel):
    livekit_token: str
    room_name: str
    session: SessionResponse
    participants: List[ParticipantResponse] = []
