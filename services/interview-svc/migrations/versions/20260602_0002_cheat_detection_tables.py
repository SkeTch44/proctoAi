"""cheat detection tables

Revision ID: 20260602_0002
Revises: 20260601_0001
Create Date: 2026-06-02 00:00:00

Creates cheat_alerts and cheat_monitoring_states tables
for real-time interview cheat detection.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260602_0002"
down_revision: Union[str, None] = "20260601_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- cheat_alerts ----------
    op.create_table(
        "cheat_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("evidence_snapshot", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "acknowledged",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("acknowledged_by", sa.Integer, nullable=True),
        sa.Column("acknowledged_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_cheat_alerts_session_id", "cheat_alerts", ["session_id"]
    )

    # ---------- cheat_monitoring_states ----------
    op.create_table(
        "cheat_monitoring_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="inactive",
        ),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("stopped_at", sa.DateTime, nullable=True),
        sa.Column(
            "total_frames_processed",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "total_events_processed",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "total_alerts_generated",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "current_risk_score",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "current_verdict",
            sa.String(20),
            nullable=False,
            server_default="SAFE",
        ),
        sa.Column("config", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("cheat_monitoring_states")
    op.drop_table("cheat_alerts")
