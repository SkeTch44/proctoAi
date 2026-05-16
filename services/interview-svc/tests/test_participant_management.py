"""Unit tests for InterviewSessionService.list_participants and remove_participant."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import PermissionDeniedError, SessionNotFoundError
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
    livekit.remove_participant = AsyncMock()
    return livekit


@pytest.fixture
def service(mock_db, mock_livekit):
    """Create an InterviewSessionService with mocked dependencies."""
    return InterviewSessionService(db=mock_db, livekit=mock_livekit)


def _make_session(session_id="sess-123", creator_id=1, status="active"):
    """Helper to create a mock InterviewSession."""
    session = MagicMock(spec=InterviewSession)
    session.id = session_id
    session.creator_id = creator_id
    session.status = status
    session.room_name = f"interview_{session_id[:8]}"
    session.max_participants = 6
    return session


def _make_participant(
    session_id="sess-123",
    user_id=10,
    role="interviewee",
    display_name="Test User",
    status="connected",
):
    """Helper to create a mock SessionParticipant."""
    participant = MagicMock(spec=SessionParticipant)
    participant.session_id = session_id
    participant.user_id = user_id
    participant.role = role
    participant.display_name = display_name
    participant.status = status
    participant.joined_at = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    participant.left_at = None
    return participant


def _setup_db_execute(mock_db, results_sequence):
    """Configure mock_db.execute to return a sequence of results.

    Each entry in results_sequence should be a value that scalar_one_or_none()
    or scalars().all() will return.
    """
    execute_results = []
    for result in results_sequence:
        mock_result = MagicMock()
        if isinstance(result, list):
            # For scalars().all() pattern
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = result
            mock_result.scalars.return_value = mock_scalars
        else:
            # For scalar_one_or_none() pattern
            mock_result.scalar_one_or_none.return_value = result
        execute_results.append(mock_result)

    mock_db.execute = AsyncMock(side_effect=execute_results)


class TestListParticipants:
    """Tests for list_participants method."""

    @pytest.mark.asyncio
    async def test_raises_session_not_found_for_nonexistent_session(
        self, service, mock_db
    ):
        _setup_db_execute(mock_db, [None])

        with pytest.raises(SessionNotFoundError):
            await service.list_participants("nonexistent-id")

    @pytest.mark.asyncio
    async def test_returns_all_participants_for_session(self, service, mock_db):
        session = _make_session()
        participants = [
            _make_participant(user_id=1, role="interviewer", display_name="Alice"),
            _make_participant(user_id=2, role="interviewee", display_name="Bob"),
            _make_participant(user_id=3, role="observer", display_name="Charlie"),
        ]
        _setup_db_execute(mock_db, [session, participants])

        result = await service.list_participants("sess-123")

        assert len(result) == 3
        assert result[0].user_id == 1
        assert result[1].user_id == 2
        assert result[2].user_id == 3

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_participants(self, service, mock_db):
        session = _make_session()
        _setup_db_execute(mock_db, [session, []])

        result = await service.list_participants("sess-123")

        assert result == []

    @pytest.mark.asyncio
    async def test_includes_participant_fields(self, service, mock_db):
        session = _make_session()
        participant = _make_participant(
            user_id=5,
            role="interviewer",
            display_name="Jane",
            status="connected",
        )
        _setup_db_execute(mock_db, [session, [participant]])

        result = await service.list_participants("sess-123")

        assert len(result) == 1
        p = result[0]
        assert p.user_id == 5
        assert p.display_name == "Jane"
        assert p.role == "interviewer"
        assert p.status == "connected"
        assert p.joined_at is not None


class TestRemoveParticipant:
    """Tests for remove_participant method."""

    @pytest.mark.asyncio
    async def test_raises_session_not_found_for_nonexistent_session(
        self, service, mock_db
    ):
        _setup_db_execute(mock_db, [None])

        with pytest.raises(SessionNotFoundError):
            await service.remove_participant("nonexistent-id", user_id=10, removed_by=1)

    @pytest.mark.asyncio
    async def test_raises_permission_denied_if_caller_not_interviewer(
        self, service, mock_db
    ):
        session = _make_session(creator_id=99)  # caller (user 5) is not creator
        # Second query: caller is not an interviewer participant
        _setup_db_execute(mock_db, [session, None])

        with pytest.raises(PermissionDeniedError):
            await service.remove_participant("sess-123", user_id=10, removed_by=5)

    @pytest.mark.asyncio
    async def test_creator_can_remove_participant(self, service, mock_db, mock_livekit):
        session = _make_session(creator_id=1)
        target = _make_participant(user_id=10, role="interviewee")
        # First query: session, second query: target participant
        _setup_db_execute(mock_db, [session, target])

        await service.remove_participant("sess-123", user_id=10, removed_by=1)

        assert target.status == "removed"
        assert target.left_at is not None
        mock_db.commit.assert_called_once()
        mock_livekit.remove_participant.assert_called_once_with(
            room_name="interview_sess-123",
            identity="10",
        )

    @pytest.mark.asyncio
    async def test_interviewer_participant_can_remove(
        self, service, mock_db, mock_livekit
    ):
        session = _make_session(creator_id=99)  # caller (user 5) is not creator
        caller = _make_participant(user_id=5, role="interviewer")
        target = _make_participant(user_id=10, role="interviewee")
        # First query: session, second: caller check, third: target
        _setup_db_execute(mock_db, [session, caller, target])

        await service.remove_participant("sess-123", user_id=10, removed_by=5)

        assert target.status == "removed"
        assert target.left_at is not None
        mock_livekit.remove_participant.assert_called_once_with(
            room_name="interview_sess-123",
            identity="10",
        )

    @pytest.mark.asyncio
    async def test_raises_not_found_if_target_participant_missing(
        self, service, mock_db
    ):
        session = _make_session(creator_id=1)
        # First query: session, second: target not found
        _setup_db_execute(mock_db, [session, None])

        with pytest.raises(SessionNotFoundError, match="not found in session"):
            await service.remove_participant("sess-123", user_id=999, removed_by=1)

    @pytest.mark.asyncio
    async def test_calls_livekit_remove_participant(
        self, service, mock_db, mock_livekit
    ):
        session = _make_session(creator_id=1)
        target = _make_participant(user_id=10)
        _setup_db_execute(mock_db, [session, target])

        await service.remove_participant("sess-123", user_id=10, removed_by=1)

        mock_livekit.remove_participant.assert_called_once_with(
            room_name="interview_sess-123",
            identity="10",
        )

    @pytest.mark.asyncio
    async def test_records_left_at_timestamp(self, service, mock_db, mock_livekit):
        session = _make_session(creator_id=1)
        target = _make_participant(user_id=10)
        target.left_at = None
        _setup_db_execute(mock_db, [session, target])

        await service.remove_participant("sess-123", user_id=10, removed_by=1)

        assert target.left_at is not None
        assert isinstance(target.left_at, datetime)
