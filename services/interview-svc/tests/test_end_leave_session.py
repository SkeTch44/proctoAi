"""Unit tests for InterviewSessionService.end_session and leave_session."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    InvalidSessionStateError,
    PermissionDeniedError,
    SessionNotFoundError,
)
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.session_service import InterviewSessionService


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_livekit():
    """Create a mock LiveKit adapter."""
    livekit = AsyncMock()
    livekit.delete_room = AsyncMock()
    livekit.create_room = AsyncMock(return_value={"name": "test_room"})
    return livekit


@pytest.fixture
def service(mock_db, mock_livekit):
    """Create an InterviewSessionService with mocked dependencies."""
    return InterviewSessionService(db=mock_db, livekit=mock_livekit)


def _make_session(
    session_id="session-123",
    status="active",
    creator_id=42,
    room_name="interview_session-",
):
    """Helper to create a mock InterviewSession."""
    session = MagicMock(spec=InterviewSession)
    session.id = session_id
    session.status = status
    session.creator_id = creator_id
    session.room_name = room_name
    session.ended_at = None
    return session


def _make_participant(user_id, role="interviewer", status="connected"):
    """Helper to create a mock SessionParticipant."""
    p = MagicMock(spec=SessionParticipant)
    p.user_id = user_id
    p.role = role
    p.status = status
    p.left_at = None
    return p


class TestEndSession:
    """Tests for end_session method."""

    @pytest.mark.asyncio
    async def test_session_not_found_raises_error(self, service, mock_db):
        """end_session raises SessionNotFoundError for non-existent session."""
        # Mock: session query returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(SessionNotFoundError):
            await service.end_session(session_id="nonexistent", ended_by=1)

    @pytest.mark.asyncio
    async def test_permission_denied_for_non_creator_non_interviewer(
        self, service, mock_db
    ):
        """end_session raises PermissionDeniedError if caller is not creator or interviewer."""
        session = _make_session(creator_id=42)

        # First call returns session, second call returns no interviewer participant
        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_participant_result = MagicMock()
        mock_participant_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_participant_result]
        )

        with pytest.raises(PermissionDeniedError):
            await service.end_session(session_id="session-123", ended_by=999)

    @pytest.mark.asyncio
    async def test_creator_can_end_session(self, service, mock_db, mock_livekit):
        """Session creator can end the session."""
        session = _make_session(creator_id=42, status="active")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        # For connected participants query
        mock_participants_result = MagicMock()
        mock_participants_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_participants_result]
        )

        result = await service.end_session(session_id="session-123", ended_by=42)

        assert result.status == "ended"
        assert result.ended_at is not None
        mock_db.commit.assert_called_once()
        mock_livekit.delete_room.assert_called_once_with(session.room_name)

    @pytest.mark.asyncio
    async def test_interviewer_participant_can_end_session(
        self, service, mock_db, mock_livekit
    ):
        """An interviewer participant (not creator) can end the session."""
        session = _make_session(creator_id=42, status="active")
        interviewer = _make_participant(user_id=99, role="interviewer")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_participant_result = MagicMock()
        mock_participant_result.scalar_one_or_none.return_value = interviewer

        # For connected participants query
        mock_connected_result = MagicMock()
        mock_connected_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_session_result,
                mock_participant_result,
                mock_connected_result,
            ]
        )

        result = await service.end_session(session_id="session-123", ended_by=99)

        assert result.status == "ended"
        mock_livekit.delete_room.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_transition_from_ended(self, service, mock_db):
        """Cannot end an already-ended session."""
        session = _make_session(status="ended")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_db.execute = AsyncMock(return_value=mock_session_result)

        with pytest.raises(InvalidSessionStateError):
            await service.end_session(session_id="session-123", ended_by=42)

    @pytest.mark.asyncio
    async def test_scheduled_session_can_be_ended(self, service, mock_db, mock_livekit):
        """A scheduled session can be ended directly (scheduled→ended is valid)."""
        session = _make_session(creator_id=42, status="scheduled")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_connected_result = MagicMock()
        mock_connected_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_connected_result]
        )

        result = await service.end_session(session_id="session-123", ended_by=42)

        assert result.status == "ended"

    @pytest.mark.asyncio
    async def test_disconnects_all_connected_participants(
        self, service, mock_db, mock_livekit
    ):
        """end_session sets all connected participants to disconnected."""
        session = _make_session(creator_id=42, status="active")
        p1 = _make_participant(user_id=1, status="connected")
        p2 = _make_participant(user_id=2, status="connected")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_connected_result = MagicMock()
        mock_connected_result.scalars.return_value.all.return_value = [p1, p2]

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_connected_result]
        )

        await service.end_session(session_id="session-123", ended_by=42)

        assert p1.status == "disconnected"
        assert p1.left_at is not None
        assert p2.status == "disconnected"
        assert p2.left_at is not None

    @pytest.mark.asyncio
    async def test_calls_delete_room(self, service, mock_db, mock_livekit):
        """end_session calls LiveKitAdapter.delete_room."""
        session = _make_session(creator_id=42, status="active", room_name="interview_abc")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_connected_result = MagicMock()
        mock_connected_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_connected_result]
        )

        await service.end_session(session_id="session-123", ended_by=42)

        mock_livekit.delete_room.assert_called_once_with("interview_abc")


class TestLeaveSession:
    """Tests for leave_session method."""

    @pytest.mark.asyncio
    async def test_session_not_found_raises_error(self, service, mock_db):
        """leave_session raises SessionNotFoundError for non-existent session."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(SessionNotFoundError):
            await service.leave_session(session_id="nonexistent", user_id=1)

    @pytest.mark.asyncio
    async def test_participant_not_found_raises_error(self, service, mock_db):
        """leave_session raises error if participant not in session."""
        session = _make_session()

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_participant_result = MagicMock()
        mock_participant_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_participant_result]
        )

        with pytest.raises(SessionNotFoundError, match="not found"):
            await service.leave_session(session_id="session-123", user_id=999)

    @pytest.mark.asyncio
    async def test_sets_participant_to_disconnected(self, service, mock_db):
        """leave_session sets participant status to disconnected."""
        session = _make_session()
        participant = _make_participant(user_id=5, status="connected")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_participant_result = MagicMock()
        mock_participant_result.scalar_one_or_none.return_value = participant

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_participant_result]
        )

        await service.leave_session(session_id="session-123", user_id=5)

        assert participant.status == "disconnected"
        assert participant.left_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_records_left_at_timestamp(self, service, mock_db):
        """leave_session records the left_at timestamp."""
        session = _make_session()
        participant = _make_participant(user_id=7, status="connected")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_participant_result = MagicMock()
        mock_participant_result.scalar_one_or_none.return_value = participant

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_participant_result]
        )

        before = datetime.now(UTC)
        await service.leave_session(session_id="session-123", user_id=7)

        assert participant.left_at is not None


class TestStatusMonotonicity:
    """Tests for status transition enforcement."""

    @pytest.mark.asyncio
    async def test_cannot_transition_ended_to_active(self, service, mock_db):
        """Cannot go from ended back to active."""
        session = _make_session(status="ended")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_db.execute = AsyncMock(return_value=mock_session_result)

        with pytest.raises(InvalidSessionStateError):
            await service.end_session(session_id="session-123", ended_by=42)

    @pytest.mark.asyncio
    async def test_active_to_ended_is_valid(self, service, mock_db, mock_livekit):
        """active → ended is a valid transition."""
        session = _make_session(creator_id=42, status="active")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_connected_result = MagicMock()
        mock_connected_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_connected_result]
        )

        result = await service.end_session(session_id="session-123", ended_by=42)
        assert result.status == "ended"

    @pytest.mark.asyncio
    async def test_scheduled_to_ended_is_valid(self, service, mock_db, mock_livekit):
        """scheduled → ended is a valid transition."""
        session = _make_session(creator_id=42, status="scheduled")

        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = session

        mock_connected_result = MagicMock()
        mock_connected_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_connected_result]
        )

        result = await service.end_session(session_id="session-123", ended_by=42)
        assert result.status == "ended"
