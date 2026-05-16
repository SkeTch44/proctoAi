"""Unit tests for InterviewSessionService.join_session, get_session, list_sessions."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    DuplicateIntervieweeError,
    DuplicateParticipantError,
    ParticipantRemovedError,
    SessionEndedError,
    SessionFullError,
    SessionNotFoundError,
)
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.session_service import (
    InterviewSessionService,
    JoinResult,
)


def _make_session(
    session_id="sess-1234",
    status="scheduled",
    max_participants=6,
    room_name="interview_sess-123",
):
    """Create a mock InterviewSession."""
    session = MagicMock(spec=InterviewSession)
    session.id = session_id
    session.status = status
    session.max_participants = max_participants
    session.room_name = room_name
    session.title = "Test Interview"
    session.creator_id = 1
    session.started_at = None
    session.ended_at = None
    session.scheduled_at = None
    session.created_at = datetime(2025, 1, 1)
    return session


def _make_participant(
    user_id=10,
    session_id="sess-1234",
    role="interviewer",
    status="connected",
    display_name="Test User",
):
    """Create a mock SessionParticipant."""
    p = MagicMock(spec=SessionParticipant)
    p.id = 1
    p.user_id = user_id
    p.session_id = session_id
    p.role = role
    p.status = status
    p.display_name = display_name
    p.joined_at = datetime(2025, 1, 1)
    p.left_at = None
    return p


class _MockScalarResult:
    """Helper to mock db.execute().scalar_one_or_none() and .scalar()."""

    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        if isinstance(self._value, list):
            return self._value
        return [self._value] if self._value else []


def _build_service_with_execute_sequence(execute_returns, livekit_token="tok_abc"):
    """Build a service with a mock db that returns values in sequence from execute calls."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    # Each call to db.execute returns the next item in the sequence
    db.execute = AsyncMock(side_effect=execute_returns)

    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value=livekit_token)

    service = InterviewSessionService(db=db, livekit=livekit)
    return service, db, livekit


class TestJoinSessionValidation:
    """Tests for session validation in join_session."""

    @pytest.mark.asyncio
    async def test_raises_session_not_found_when_session_missing(self):
        # execute returns: session query -> None
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(None),  # session lookup
        ])

        with pytest.raises(SessionNotFoundError):
            await service.join_session(
                session_id="nonexistent",
                user_id=10,
                role="interviewer",
                display_name="Alice",
            )

    @pytest.mark.asyncio
    async def test_raises_session_ended_when_status_ended(self):
        session = _make_session(status="ended")
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
        ])

        with pytest.raises(SessionEndedError):
            await service.join_session(
                session_id="sess-1234",
                user_id=10,
                role="interviewer",
                display_name="Alice",
            )

    @pytest.mark.asyncio
    async def test_raises_session_full_when_at_capacity(self):
        session = _make_session(status="active", max_participants=2)
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(2),  # count of connected participants
        ])

        with pytest.raises(SessionFullError):
            await service.join_session(
                session_id="sess-1234",
                user_id=10,
                role="interviewer",
                display_name="Alice",
            )

    @pytest.mark.asyncio
    async def test_raises_duplicate_interviewee_when_one_exists(self):
        session = _make_session(status="active")
        existing_interviewee = _make_participant(
            user_id=99, role="interviewee", status="connected"
        )
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(1),  # count of connected participants
            _MockScalarResult(existing_interviewee),  # existing interviewee check
        ])

        with pytest.raises(DuplicateIntervieweeError):
            await service.join_session(
                session_id="sess-1234",
                user_id=10,
                role="interviewee",
                display_name="Bob",
            )

    @pytest.mark.asyncio
    async def test_raises_participant_removed_when_status_removed(self):
        session = _make_session(status="active")
        removed_participant = _make_participant(user_id=10, status="removed")
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(1),  # count of connected participants
            _MockScalarResult(removed_participant),  # existing participant (removed)
        ])

        with pytest.raises(ParticipantRemovedError):
            await service.join_session(
                session_id="sess-1234",
                user_id=10,
                role="interviewer",
                display_name="Alice",
            )

    @pytest.mark.asyncio
    async def test_raises_duplicate_participant_when_already_connected(self):
        session = _make_session(status="active")
        connected_participant = _make_participant(user_id=10, status="connected")
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(1),  # count of connected participants
            _MockScalarResult(connected_participant),  # existing participant (connected)
        ])

        with pytest.raises(DuplicateParticipantError):
            await service.join_session(
                session_id="sess-1234",
                user_id=10,
                role="interviewer",
                display_name="Alice",
            )


class TestJoinSessionRejoin:
    """Tests for rejoin logic in join_session."""

    @pytest.mark.asyncio
    async def test_reactivates_disconnected_participant(self):
        session = _make_session(status="active")
        disconnected = _make_participant(user_id=10, status="disconnected")
        participants_list = [disconnected]

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(1),  # count of connected participants
            _MockScalarResult(disconnected),  # existing participant (disconnected)
            _MockScalarResult(participants_list),  # participant list
        ])

        result = await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewer",
            display_name="Alice",
        )

        # Verify the participant was reactivated
        assert disconnected.status == "connected"
        assert disconnected.left_at is None
        assert isinstance(result, JoinResult)

    @pytest.mark.asyncio
    async def test_rejoin_does_not_create_new_record(self):
        session = _make_session(status="active")
        disconnected = _make_participant(user_id=10, status="disconnected")
        participants_list = [disconnected]

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(1),  # count of connected participants
            _MockScalarResult(disconnected),  # existing participant (disconnected)
            _MockScalarResult(participants_list),  # participant list
        ])

        await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewer",
            display_name="Alice",
        )

        # db.add should NOT be called for rejoin
        db.add.assert_not_called()


class TestJoinSessionNewParticipant:
    """Tests for new participant creation in join_session."""

    @pytest.mark.asyncio
    async def test_creates_new_participant_record(self):
        session = _make_session(status="active")
        participants_list = []

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(0),  # count of connected participants
            _MockScalarResult(None),  # no existing participant
            _MockScalarResult(participants_list),  # participant list
        ])

        result = await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewer",
            display_name="Alice",
        )

        # db.add should be called with a new participant
        db.add.assert_called_once()
        new_participant = db.add.call_args[0][0]
        assert new_participant.session_id == "sess-1234"
        assert new_participant.user_id == 10
        assert new_participant.role == "interviewer"
        assert new_participant.display_name == "Alice"
        assert new_participant.status == "connected"

    @pytest.mark.asyncio
    async def test_returns_join_result_with_token(self):
        session = _make_session(status="active")
        participants_list = []

        service, db, livekit = _build_service_with_execute_sequence(
            [
                _MockScalarResult(session),
                _MockScalarResult(0),
                _MockScalarResult(None),
                _MockScalarResult(participants_list),
            ],
            livekit_token="eyJ_test_token",
        )

        result = await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewer",
            display_name="Alice",
        )

        assert isinstance(result, JoinResult)
        assert result.livekit_token == "eyJ_test_token"
        assert result.room_name == "interview_sess-123"
        assert result.session == session

    @pytest.mark.asyncio
    async def test_generates_token_with_correct_params(self):
        session = _make_session(status="active")
        participants_list = []

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),
            _MockScalarResult(0),
            _MockScalarResult(None),
            _MockScalarResult(participants_list),
        ])

        await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="observer",
            display_name="Charlie",
        )

        livekit.generate_token.assert_called_once_with(
            room_name="interview_sess-123",
            identity="10",
            name="Charlie",
            role="observer",
        )


class TestJoinSessionStatusTransition:
    """Tests for session status transition on first join."""

    @pytest.mark.asyncio
    async def test_transitions_scheduled_to_active_on_first_join(self):
        session = _make_session(status="scheduled")
        participants_list = []

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),
            _MockScalarResult(0),
            _MockScalarResult(None),
            _MockScalarResult(participants_list),
        ])

        await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewer",
            display_name="Alice",
        )

        assert session.status == "active"
        assert session.started_at is not None

    @pytest.mark.asyncio
    async def test_does_not_transition_active_session(self):
        session = _make_session(status="active")
        session.started_at = datetime(2025, 1, 1, 10, 0)
        participants_list = []

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),
            _MockScalarResult(1),
            _MockScalarResult(None),
            _MockScalarResult(participants_list),
        ])

        await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewer",
            display_name="Alice",
        )

        # started_at should remain unchanged
        assert session.started_at == datetime(2025, 1, 1, 10, 0)


class TestJoinSessionIntervieweeConstraint:
    """Tests for the single interviewee constraint."""

    @pytest.mark.asyncio
    async def test_allows_first_interviewee(self):
        session = _make_session(status="active")
        participants_list = []

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(0),  # count of connected participants
            _MockScalarResult(None),  # no existing interviewee
            _MockScalarResult(None),  # no existing participant for this user
            _MockScalarResult(participants_list),  # participant list
        ])

        result = await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewee",
            display_name="Candidate",
        )

        assert isinstance(result, JoinResult)

    @pytest.mark.asyncio
    async def test_interviewer_role_skips_interviewee_check(self):
        session = _make_session(status="active")
        participants_list = []

        service, db, livekit = _build_service_with_execute_sequence([
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(1),  # count of connected participants
            # No interviewee check query for interviewer role
            _MockScalarResult(None),  # no existing participant for this user
            _MockScalarResult(participants_list),  # participant list
        ])

        result = await service.join_session(
            session_id="sess-1234",
            user_id=10,
            role="interviewer",
            display_name="Alice",
        )

        assert isinstance(result, JoinResult)


class TestGetSession:
    """Tests for get_session method."""

    @pytest.mark.asyncio
    async def test_returns_session_when_found(self):
        session = _make_session()
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(session),
        ])

        result = await service.get_session("sess-1234")
        assert result == session

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        service, db, _ = _build_service_with_execute_sequence([
            _MockScalarResult(None),
        ])

        result = await service.get_session("nonexistent")
        assert result is None


class TestListSessions:
    """Tests for list_sessions method."""

    @pytest.mark.asyncio
    async def test_returns_sessions_for_user(self):
        sessions = [_make_session(session_id="s1"), _make_session(session_id="s2")]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sessions
        mock_result.scalars.return_value = mock_scalars

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        livekit = MagicMock()

        service = InterviewSessionService(db=db, livekit=livekit)
        result = await service.list_sessions(user_id=42)

        assert result == sessions
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_sessions(self):
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        livekit = MagicMock()

        service = InterviewSessionService(db=db, livekit=livekit)
        result = await service.list_sessions(user_id=999)

        assert result == []
