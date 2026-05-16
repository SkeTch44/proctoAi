from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base


class CheatMonitoringState(Base):
    __tablename__ = "cheat_monitoring_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("interview_sessions.id"),
        unique=True,
        nullable=False,
    )
    status = Column(String(20), default="inactive")  # inactive, active, paused
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    total_frames_processed = Column(Integer, default=0)
    total_events_processed = Column(Integer, default=0)
    total_alerts_generated = Column(Integer, default=0)
    current_risk_score = Column(Float, default=0.0)
    current_verdict = Column(String(20), default="SAFE")
    config = Column(JSON, nullable=True)  # Per-session detection config overrides
