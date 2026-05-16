"""baseline schema

Revision ID: 20260512_0001
Revises:
Create Date: 2026-05-12 20:30:00

Initial schema matching the current SQLite database. Creates all tables
at their current shape so Alembic has a starting point from which to
evolve the schema going forward.

Safe to run against:
  - A fresh DB (creates tables)
  - An existing DB (idempotent - uses IF NOT EXISTS via op.create_table
    guarded by checkfirst=True)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260512_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def upgrade() -> None:
    # ---------- users ----------
    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("username", sa.String(150), unique=True, nullable=False),
            sa.Column("email", sa.String(255), unique=True, nullable=True),
            sa.Column("password_hash", sa.Text, nullable=False),
            sa.Column("role", sa.String(20), server_default="student"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("last_login", sa.DateTime, nullable=True),
            sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
            sa.Column("login_attempts", sa.Integer, server_default="0"),
            sa.Column("locked_until", sa.DateTime, nullable=True),
            sa.CheckConstraint(
                "role IN ('student', 'teacher', 'admin')", name="ck_users_role"
            ),
        )
        op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ---------- exams ----------
    if not _has_table("exams"):
        op.create_table(
            "exams",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text, server_default=""),
            sa.Column("questions", sa.Text, nullable=False),
            sa.Column("duration", sa.Integer, server_default="3600"),
            sa.Column(
                "created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    # ---------- sessions ----------
    if not _has_table("sessions"):
        op.create_table(
            "sessions",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("exam_id", sa.Integer, sa.ForeignKey("exams.id"), nullable=False),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("answers", sa.Text, nullable=True),
            sa.Column("score", sa.Float, server_default="0"),
            sa.Column("suspicion_score", sa.Integer, server_default="0"),
            sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime, nullable=True),
            sa.Column("status", sa.String(20), server_default="active"),
        )
        op.create_index("ix_sessions_exam_id", "sessions", ["exam_id"])
        op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    # ---------- proctoring_events ----------
    if not _has_table("proctoring_events"):
        op.create_table(
            "proctoring_events",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "session_id", sa.Integer, sa.ForeignKey("sessions.id"), nullable=False
            ),
            sa.Column("event_type", sa.String(100), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("details", sa.Text, nullable=True),
            sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_events_session_id", "proctoring_events", ["session_id"]
        )

    # ---------- question_banks ----------
    if not _has_table("question_banks"):
        op.create_table(
            "question_banks",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(500), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("subject", sa.String(200), nullable=True),
            sa.Column(
                "created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("is_public", sa.Boolean, server_default=sa.text("false")),
            sa.Column("is_template", sa.Boolean, server_default=sa.text("false")),
            sa.Column("tags", sa.Text, nullable=True),
            sa.Column("metadata", sa.Text, nullable=True),
        )

    # ---------- questions ----------
    if not _has_table("questions"):
        op.create_table(
            "questions",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("uuid", sa.String(36), unique=True, nullable=False),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("question_text", sa.Text, nullable=False),
            sa.Column("question_type", sa.String(50), nullable=False),
            sa.Column("difficulty", sa.String(20), server_default="medium"),
            sa.Column("points", sa.Integer, server_default="1"),
            sa.Column("time_limit", sa.Integer, nullable=True),
            sa.Column("subject", sa.String(200), nullable=True),
            sa.Column("topic", sa.String(200), nullable=True),
            sa.Column("subtopic", sa.String(200), nullable=True),
            sa.Column("learning_objective", sa.Text, nullable=True),
            sa.Column("bloom_level", sa.String(50), server_default="knowledge"),
            sa.Column("question_data", sa.Text, nullable=False),
            sa.Column("explanation", sa.Text, nullable=True),
            sa.Column("hints", sa.Text, nullable=True),
            sa.Column("tags", sa.Text, nullable=True),
            sa.Column(
                "created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("status", sa.String(20), server_default="draft"),
            sa.Column("usage_count", sa.Integer, server_default="0"),
            sa.Column("average_score", sa.Float, server_default="0.0"),
            sa.Column("difficulty_rating", sa.Float, server_default="0.0"),
            sa.Column("version", sa.Integer, server_default="1"),
            sa.Column(
                "parent_id", sa.Integer, sa.ForeignKey("questions.id"), nullable=True
            ),
            sa.Column("content_hash", sa.String(64), nullable=True),
        )
        op.create_index("ix_questions_uuid", "questions", ["uuid"], unique=True)
        op.create_index("ix_questions_type", "questions", ["question_type"])
        op.create_index("ix_questions_difficulty", "questions", ["difficulty"])
        op.create_index("ix_questions_subject", "questions", ["subject"])
        op.create_index("ix_questions_topic", "questions", ["topic"])
        op.create_index("ix_questions_status", "questions", ["status"])
        op.create_index("ix_questions_created_by", "questions", ["created_by"])

    # ---------- question_bank_items ----------
    if not _has_table("question_bank_items"):
        op.create_table(
            "question_bank_items",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "bank_id",
                sa.Integer,
                sa.ForeignKey("question_banks.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "question_id",
                sa.Integer,
                sa.ForeignKey("questions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("order_index", sa.Integer, server_default="0"),
            sa.Column("added_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column(
                "added_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column("weight", sa.Float, server_default="1.0"),
            sa.Column("is_mandatory", sa.Boolean, server_default=sa.text("false")),
            sa.UniqueConstraint("bank_id", "question_id", name="uq_qbi_bank_question"),
        )
        op.create_index("ix_qbi_bank_id", "question_bank_items", ["bank_id"])
        op.create_index(
            "ix_qbi_question_id", "question_bank_items", ["question_id"]
        )

    # ---------- question_reviews ----------
    if not _has_table("question_reviews"):
        op.create_table(
            "question_reviews",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "question_id",
                sa.Integer,
                sa.ForeignKey("questions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "reviewer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("rating", sa.Integer, nullable=True),
            sa.Column("difficulty_rating", sa.Integer, nullable=True),
            sa.Column("quality_rating", sa.Integer, nullable=True),
            sa.Column("comments", sa.Text, nullable=True),
            sa.Column("reviewed_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "question_id", "reviewer_id", name="uq_qr_question_reviewer"
            ),
        )

    # ---------- question_usage_stats ----------
    if not _has_table("question_usage_stats"):
        op.create_table(
            "question_usage_stats",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "question_id",
                sa.Integer,
                sa.ForeignKey("questions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("exam_id", sa.Integer, nullable=True),
            sa.Column("session_id", sa.Integer, nullable=True),
            sa.Column("student_answer", sa.Text, nullable=True),
            sa.Column("is_correct", sa.Boolean, nullable=True),
            sa.Column("score", sa.Float, nullable=True),
            sa.Column("time_taken", sa.Integer, nullable=True),
            sa.Column("used_at", sa.DateTime, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("question_usage_stats")
    op.drop_table("question_reviews")
    op.drop_table("question_bank_items")
    op.drop_table("questions")
    op.drop_table("question_banks")
    op.drop_table("proctoring_events")
    op.drop_table("sessions")
    op.drop_table("exams")
    op.drop_table("users")
