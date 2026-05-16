"""
Coding problem models — coding-svc owns these tables.
"""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func
from app.core.database import Base


class Problem(Base):
    __tablename__ = "coding_problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String(20), default="medium")
    # Starter code templates per language (JSON: {"python": "...", "javascript": "..."})
    starter_code = Column(Text, default="{}")
    # Constraints text
    constraints = Column(Text, default="")
    # Tags for filtering
    tags = Column(Text, default="[]")  # JSON list
    time_limit_ms = Column(Integer, default=2000)
    memory_limit_kb = Column(Integer, default=256000)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)


class TestCase(Base):
    __tablename__ = "coding_testcases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, nullable=False, index=True)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_sample = Column(Boolean, default=False)  # Visible to student
    is_hidden = Column(Boolean, default=True)   # Used for grading only
    weight = Column(Float, default=1.0)         # Partial credit weight
    order_index = Column(Integer, default=0)


class Submission(Base):
    __tablename__ = "coding_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(Integer, nullable=True)  # Links to exam/interview session
    language = Column(String(50), nullable=False)
    source_code = Column(Text, nullable=False)
    # Judge0 result
    status = Column(String(50), default="pending")  # pending, running, accepted, wrong_answer, TLE, MLE, RE, CE
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    compile_output = Column(Text, nullable=True)
    # Scoring
    tests_passed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    # AI rubric scoring (JSON)
    ai_rubric = Column(Text, nullable=True)  # Full AI review JSON
    ai_score = Column(Float, nullable=True)  # AI total score 0-100
    # Admin review
    admin_reviewed = Column(Boolean, default=False)
    admin_score = Column(Float, nullable=True)  # Final score after admin review
    admin_feedback = Column(Text, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    # Execution metrics
    execution_time_ms = Column(Integer, nullable=True)
    memory_used_kb = Column(Integer, nullable=True)
    # Cheat signals
    paste_count = Column(Integer, default=0)
    typing_speed_wpm = Column(Float, nullable=True)
    # Timestamps
    submitted_at = Column(DateTime, default=func.now())
    judged_at = Column(DateTime, nullable=True)
