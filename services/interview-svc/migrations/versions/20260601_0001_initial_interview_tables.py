"""initial interview tables

Revision ID: 20260601_0001
Revises:
Create Date: 2026-06-01 00:00:00

Creates interview_sessions, session_participants, and presentations tables
for the interview-svc microservice.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260601_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- interview_sessions ----------
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("room_name", sa.String(100), unique=True, nullable=False),
        sa.Column("creator_id", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("max_participants", sa.Integer, nullable=False, server_default="6"),
        sa.Column("scheduled_at", sa.DateTime, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("ended_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("recording_url", sa.String(1000), nullable=True),
    )
    op.create_index(
        "ix_interview_sessions_creator_id", "interview_sessions", ["creator_id"]
    )
    op.create_index(
        "ix_interview_sessions_status", "interview_sessions", ["status"]
    )

    # ---------- session_participants ----------
    op.create_table(
        "session_participants",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("joined_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("left_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="connected"),
        sa.UniqueConstraint("user_id", "session_id", name="uq_participant_user_session"),
    )
    op.create_index(
        "ix_session_participants_session_id", "session_participants", ["session_id"]
    )
    op.create_index(
        "ix_session_participants_user_id", "session_participants", ["user_id"]
    )

    # ---------- presentations ----------
    op.create_table(
        "presentations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_url", sa.String(1000), nullable=False),
        sa.Column("slide_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_slide", sa.Integer, nullable=False, server_default="0"),
        sa.Column("slides_json", sa.Text, nullable=True),
        sa.Column("uploaded_by", sa.Integer, nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )
    op.create_index(
        "ix_presentations_session_id", "presentations", ["session_id"]
    )


def downgrade() -> None:
    op.drop_table("presentations")
    op.drop_table("session_participants")
    op.drop_table("interview_sessions")
