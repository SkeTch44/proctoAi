from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.core.database import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title = Column(String(500), nullable=False)
    room_name = Column(String(100), unique=True, nullable=False)
    creator_id = Column(Integer, nullable=False)
    status = Column(String(20), default="scheduled", nullable=False)
    max_participants = Column(Integer, default=6, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    recording_url = Column(String(1000), nullable=True)
    is_recording = Column(Boolean, default=False, nullable=False)
