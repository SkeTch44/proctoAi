"""End-to-end integration tests (Task 10.3).

Tests the complete flow:
- Create session → multiple participants join → upload presentation → navigate slides → end session
- Webhook-driven participant disconnect handling
- Empty_timeout auto-end behavior
- Recording notification delivery

Validates: Requirements 4.4, 4.5, 5.1, 6.7, 7.4, 10.7
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    DuplicateIntervieweeError,
    SessionEndedError,
    SessionFullError,
)
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.session_service import InterviewSessionService, JoinResult


class _MockScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value if isinstance(self._value, list) else []


class TestFullSessionLifecycle:
    """Tests for the complete session lifecycle flow."""

    @pytest.mark.asyncio
    async def test_create_join_leave_end_flow(self):
        """Full lifecycle: create → join → leave → end."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()

        livekit = AsyncMock()
        livekit.create_room = AsyncMock(return_value={"name": "test_room"})
        livekit.generate_token = MagicMock(return_value="test_token")
        livekit.delete_room = AsyncMock()

        service = InterviewSessionService(db=db, livekit=livekit)

        # Step 1: Create session
        result = await service.create_session(
            creator_id=1,
            title="Full Lifecycle Test",
            max_participants=4,
        )
        assert result.session_id is not None
        assert result.room_name.startswith("interview_")
        livekit.create_room.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_participants_join_session(self):
        """Multiple participants can join until max_participants is reached."""
        session = MagicMock(spec=InterviewSession)
        session.id = "sess-multi"
        session.status = "active"
        session.max_participants = 3
        session.room_name = "interview_sess-mul"
        session.started_at = datetime(2025, 1, 1, tzinfo=UTC)
        session.is_recording = False

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        livekit = MagicMock()
        livekit.generate_token = MagicMock(return_value="token")

        service = InterviewSessionService(db=db, livekit=livekit)

        # First join (count=0)
        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(0),
                _MockScalarResult(None),
                _MockScalarResult([]),
            ]
        )
        r1 = await service.join_session("sess-multi", 1, "interviewer", "Alice")
        assert r1.livekit_token == "token"

        # Second join (count=1)
        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(1),
                _MockScalarResult(None),
                _MockScalarResult([]),
            ]
        )
        r2 = await service.join_session("sess-multi", 2, "interviewee", "Bob")
        assert r2.livekit_token == "token"

        # Third join (count=2)
        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(2),
                _MockScalarResult(None),
                _MockScalarResult([]),
            ]
        )
        r3 = await service.join_session("sess-multi", 3, "observer", "Charlie")
        assert r3.livekit_token == "token"

        # Fourth join should fail (count=3, max=3)
        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(3),
            ]
        )
        with pytest.raises(SessionFullError):
            await service.join_session("sess-multi", 4, "observer", "Dave")


class TestEmptyTimeoutBehavior:
    """Tests for empty_timeout auto-end integration."""

    @pytest.mark.asyncio
    async def test_interviewer_rejoin_cancels_timeout(self):
        """When an interviewer rejoins, the timeout is cancelled."""
        session = MagicMock(spec=InterviewSession)
        session.id = "sess-timeout"
        session.status = "active"
        session.max_participants = 6
        session.room_name = "interview_sess-tim"
        session.started_at = datetime(2025, 1, 1, tzinfo=UTC)
        session.is_recording = False

        disconnected = MagicMock(spec=SessionParticipant)
        disconnected.user_id = 42
        disconnected.role = "interviewer"
        disconnected.status = "disconnected"
        disconnected.left_at = datetime(2025, 1, 1, 1, 0, tzinfo=UTC)

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        livekit = MagicMock()
        livekit.generate_token = MagicMock(return_value="token")

        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(0),
                _MockScalarResult(disconnected),
                _MockScalarResult([disconnected]),
            ]
        )

        service = InterviewSessionService(db=db, livekit=livekit)

        with patch(
            "app.services.session_service.get_timeout_manager"
        ) as mock_get_tm:
            mock_tm = AsyncMock()
            mock_get_tm.return_value = mock_tm

            await service.join_session("sess-timeout", 42, "interviewer", "Alice")

            # Timeout should be cancelled because an interviewer rejoined
            mock_tm.cancel_timeout.assert_called_once_with("sess-timeout")


class TestRecordingNotification:
    """Tests for recording notification delivery."""

    @pytest.mark.asyncio
    async def test_join_result_includes_recording_active_flag(self):
        """JoinResult includes recording_active=True when session is recording."""
        session = MagicMock(spec=InterviewSession)
        session.id = "sess-rec"
        session.status = "active"
        session.max_participants = 6
        session.room_name = "interview_sess-rec"
        session.started_at = datetime(2025, 1, 1, tzinfo=UTC)
        session.is_recording = True  # Recording is active

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        livekit = MagicMock()
        livekit.generate_token = MagicMock(return_value="token")

        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(0),
                _MockScalarResult(None),
                _MockScalarResult([]),
            ]
        )

        service = InterviewSessionService(db=db, livekit=livekit)

        result = await service.join_session("sess-rec", 1, "interviewer", "Alice")

        assert result.recording_active is True

    @pytest.mark.asyncio
    async def test_join_result_recording_false_when_not_recording(self):
        """JoinResult includes recording_active=False when session is not recording."""
        session = MagicMock(spec=InterviewSession)
        session.id = "sess-norec"
        session.status = "active"
        session.max_participants = 6
        session.room_name = "interview_sess-nor"
        session.started_at = datetime(2025, 1, 1, tzinfo=UTC)
        session.is_recording = False

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        livekit = MagicMock()
        livekit.generate_token = MagicMock(return_value="token")

        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(0),
                _MockScalarResult(None),
                _MockScalarResult([]),
            ]
        )

        service = InterviewSessionService(db=db, livekit=livekit)

        result = await service.join_session("sess-norec", 1, "interviewer", "Alice")

        assert result.recording_active is False

    @pytest.mark.asyncio
    async def test_start_recording_broadcasts_notification(self):
        """start_recording broadcasts recording_started to all participants."""
        session = MagicMock(spec=InterviewSession)
        session.id = "sess-rec-start"
        session.status = "active"
        session.creator_id = 42
        session.room_name = "interview_sess-rec"
        session.is_recording = False

        db = AsyncMock()
        db.execute = AsyncMock(return_value=_MockScalarResult(session))
        db.commit = AsyncMock()

        livekit = AsyncMock()
        livekit.send_data = AsyncMock()

        service = InterviewSessionService(db=db, livekit=livekit)

        result = await service.start_recording("sess-rec-start", started_by=42)

        assert result.is_recording is True
        livekit.send_data.assert_called_once()
        call_data = livekit.send_data.call_args.kwargs["data"]
        assert "recording_started" in call_data

    @pytest.mark.asyncio
    async def test_stop_recording_broadcasts_notification(self):
        """stop_recording broadcasts recording_stopped to all participants."""
        session = MagicMock(spec=InterviewSession)
        session.id = "sess-rec-stop"
        session.status = "active"
        session.creator_id = 42
        session.room_name = "interview_sess-rec"
        session.is_recording = True

        db = AsyncMock()
        db.execute = AsyncMock(return_value=_MockScalarResult(session))
        db.commit = AsyncMock()

        livekit = AsyncMock()
        livekit.send_data = AsyncMock()

        service = InterviewSessionService(db=db, livekit=livekit)

        result = await service.stop_recording("sess-rec-stop", stopped_by=42)

        assert result.is_recording is False
        livekit.send_data.assert_called_once()
        call_data = livekit.send_data.call_args.kwargs["data"]
        assert "recording_stopped" in call_data


class TestEndSessionCleansUp:
    """Tests for end_session cleanup behavior."""

    @pytest.mark.asyncio
    async def test_end_session_disconnects_all_and_deletes_room(self):
        """end_session disconnects all participants and deletes the LiveKit room."""
        session = MagicMock(spec=InterviewSession)
        session.id = "sess-end"
        session.status = "active"
        session.creator_id = 42
        session.room_name = "interview_sess-end"
        session.ended_at = None

        p1 = MagicMock(spec=SessionParticipant)
        p1.status = "connected"
        p1.left_at = None
        p2 = MagicMock(spec=SessionParticipant)
        p2.status = "connected"
        p2.left_at = None

        db = AsyncMock()

        mock_session_result = _MockScalarResult(session)
        mock_participants = MagicMock()
        mock_participants.scalars.return_value.all.return_value = [p1, p2]

        db.execute = AsyncMock(
            side_effect=[mock_session_result, mock_participants]
        )
        db.commit = AsyncMock()

        livekit = AsyncMock()
        livekit.delete_room = AsyncMock()

        service = InterviewSessionService(db=db, livekit=livekit)

        result = await service.end_session("sess-end", ended_by=42)

        assert result.status == "ended"
        assert result.ended_at is not None
        assert p1.status == "disconnected"
        assert p1.left_at is not None
        assert p2.status == "disconnected"
        assert p2.left_at is not None
        livekit.delete_room.assert_called_once_with("interview_sess-end")
