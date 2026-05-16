"""
SQLAlchemy declarative models — single source of truth for the DB schema.

Used by:
  - Alembic (auto-generates migrations from these models)
  - Future service code (replaces raw sqlite3 queries)

Supports both SQLite (dev) and PostgreSQL (prod).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ============================================================
# AUTH schema
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(Text, nullable=False)
    role = Column(
        String(20),
        CheckConstraint("role IN ('student', 'teacher', 'admin')"),
        default="student",
    )
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Relationships
    sessions = relationship("ExamSession", back_populates="user")
    exams_created = relationship("Exam", back_populates="creator")


# ============================================================
# EXAMS schema
# ============================================================

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    # Questions stored as JSON text (list of question dicts).
    # In Postgres we could use JSONB; keeping Text for SQLite compat.
    questions = Column(Text, nullable=False)
    duration = Column(Integer, default=3600)  # seconds
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    creator = relationship("User", back_populates="exams_created")
    sessions = relationship("ExamSession", back_populates="exam")


class ExamSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(Text, nullable=True)  # JSON
    score = Column(Float, default=0)
    suspicion_score = Column(Integer, default=0)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")

    exam = relationship("Exam", back_populates="sessions")
    user = relationship("User", back_populates="sessions")
    events = relationship("ProctoringEvent", back_populates="session")


class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    session = relationship("ExamSession", back_populates="events")


# ============================================================
# QUESTIONS schema
# ============================================================

class QuestionBank(Base):
    __tablename__ = "question_banks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    subject = Column(String(200), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_public = Column(Boolean, default=False)
    is_template = Column(Boolean, default=False)
    tags = Column(Text, nullable=True)  # JSON list
    metadata_ = Column("metadata", Text, nullable=True)  # JSON

    items = relationship("QuestionBankItem", back_populates="bank")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    difficulty = Column(String(20), default="medium")
    points = Column(Integer, default=1)
    time_limit = Column(Integer, nullable=True)
    subject = Column(String(200), nullable=True)
    topic = Column(String(200), nullable=True, index=True)
    subtopic = Column(String(200), nullable=True)
    learning_objective = Column(Text, nullable=True)
    bloom_level = Column(String(50), default="knowledge")
    question_data = Column(Text, nullable=False)  # JSON
    explanation = Column(Text, nullable=True)
    hints = Column(Text, nullable=True)  # JSON list
    tags = Column(Text, nullable=True)  # JSON list
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    status = Column(String(20), default="draft", index=True)
    usage_count = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)
    difficulty_rating = Column(Float, default=0.0)
    version = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    content_hash = Column(String(64), nullable=True)

    bank_items = relationship("QuestionBankItem", back_populates="question")


class QuestionBankItem(Base):
    __tablename__ = "question_bank_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(Integer, ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, default=0)
    added_at = Column(DateTime, default=func.now())
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    weight = Column(Float, default=1.0)
    is_mandatory = Column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("bank_id", "question_id"),)

    bank = relationship("QuestionBank", back_populates="items")
    question = relationship("Question", back_populates="bank_items")


class QuestionReview(Base):
    __tablename__ = "question_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=True)
    difficulty_rating = Column(Integer, nullable=True)
    quality_rating = Column(Integer, nullable=True)
    comments = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=func.now())

    __table_args__ = (UniqueConstraint("question_id", "reviewer_id"),)


class QuestionUsageStat(Base):
    __tablename__ = "question_usage_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    exam_id = Column(Integer, nullable=True)
    session_id = Column(Integer, nullable=True)
    student_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    time_taken = Column(Integer, nullable=True)
    used_at = Column(DateTime, default=func.now())


# ============================================================
# Indexes (explicit for Postgres performance)
# ============================================================
Index("idx_questions_type", Question.question_type)
Index("idx_questions_difficulty", Question.difficulty)
Index("idx_questions_subject", Question.subject)
Index("idx_questions_created_by", Question.created_by)
Index("idx_qbi_bank_id", QuestionBankItem.bank_id)
Index("idx_qbi_question_id", QuestionBankItem.question_id)
Index("idx_sessions_exam_id", ExamSession.exam_id)
Index("idx_sessions_user_id", ExamSession.user_id)
Index("idx_events_session_id", ProctoringEvent.session_id)
