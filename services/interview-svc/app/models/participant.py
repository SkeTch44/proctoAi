from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.core.database import Base


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_participant_user_session"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), ForeignKey("interview_sessions.id"), nullable=False
    )
    user_id = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    display_name = Column(String(200), nullable=False)
    joined_at = Column(DateTime, default=func.now())
    left_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="connected", nullable=False)
