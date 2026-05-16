from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class Presentation(Base):
    __tablename__ = "presentations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(
        String(36), ForeignKey("interview_sessions.id"), nullable=False
    )
    filename = Column(String(500), nullable=False)
    file_url = Column(String(1000), nullable=False)
    slide_count = Column(Integer, default=0, nullable=False)
    current_slide = Column(Integer, default=0, nullable=False)
    slides_json = Column(Text, nullable=True)
    uploaded_by = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
