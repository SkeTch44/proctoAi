from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base


class CheatAlert(Base):
    __tablename__ = "cheat_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("interview_sessions.id"),
        nullable=False,
        index=True,
    )
    alert_type = Column(String(50), nullable=False)  # TAB_SWITCH, MULTIPLE_FACES, etc.
    severity = Column(String(20), nullable=False)  # MILD, HIGH, CRITICAL
    score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    details = Column(JSON, nullable=True)  # Signal-specific metadata
    evidence_snapshot = Column(Text, nullable=True)  # Base64 frame thumbnail
    created_at = Column(DateTime, default=func.now(), nullable=False)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
