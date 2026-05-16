from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from app.core.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    questions = Column(Text, nullable=False)  # JSON
    duration = Column(Integer, default=3600)  # seconds
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())


class ExamSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    kind = Column(String(20), default="exam")  # exam | interview | coding
    answers = Column(Text, nullable=True)  # JSON
    score = Column(Float, default=0)
    suspicion_score = Column(Integer, default=0)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")
