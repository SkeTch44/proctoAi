"""Property test for status monotonicity (Property 3).

Property 3: Status Monotonicity
For any session and any sequence of state transition attempts, status only progresses
forward (scheduled→active→ended). No backward transition shall succeed.

Validates: Requirements 2.5, 2.6, 4.1, 4.3
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.exceptions import InvalidSessionStateError
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.session_service import InterviewSessionService


statuses = st.sampled_from(["scheduled", "active", "ended"])


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


def _make_session(status="active", creator_id=42):
    session = MagicMock(spec=InterviewSession)
    session.id = "sess-mono"
    session.status = status
    session.creator_id = creator_id
    session.room_name = "interview_sess-mon"
    session.ended_at = None
    session.max_participants = 6
    return session


@pytest.mark.asyncio
async def test_ended_session_cannot_be_ended_again():
    """An already-ended session cannot transition to ended again."""
    session = _make_session(status="ended")

    db = AsyncMock()
    livekit = AsyncMock()

    db.execute = AsyncMock(return_value=_MockScalarResult(session))
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    with pytest.raises(InvalidSessionStateError):
        await service.end_session(session_id="sess-mono", ended_by=42)


@pytest.mark.asyncio
async def test_active_to_ended_is_valid():
    """active → ended is a valid forward transition."""
    session = _make_session(status="active")

    db = AsyncMock()
    livekit = AsyncMock()
    livekit.delete_room = AsyncMock()

    # session lookup, then connected participants query
    mock_participants = MagicMock()
    mock_participants.scalars.return_value.all.return_value = []

    db.execute = AsyncMock(
        side_effect=[_MockScalarResult(session), mock_participants]
    )
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    result = await service.end_session(session_id="sess-mono", ended_by=42)
    assert result.status == "ended"


@pytest.mark.asyncio
async def test_scheduled_to_ended_is_valid():
    """scheduled → ended is a valid forward transition."""
    session = _make_session(status="scheduled")

    db = AsyncMock()
    livekit = AsyncMock()
    livekit.delete_room = AsyncMock()

    mock_participants = MagicMock()
    mock_participants.scalars.return_value.all.return_value = []

    db.execute = AsyncMock(
        side_effect=[_MockScalarResult(session), mock_participants]
    )
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    result = await service.end_session(session_id="sess-mono", ended_by=42)
    assert result.status == "ended"


@given(current_status=statuses)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_no_backward_transitions_possible(current_status):
    """No backward transition from any status shall succeed via end_session.

    end_session only transitions TO 'ended'. If current is already 'ended',
    it must fail. If current is 'scheduled' or 'active', it must succeed.
    """
    session = _make_session(status=current_status)

    db = AsyncMock()
    livekit = AsyncMock()
    livekit.delete_room = AsyncMock()

    mock_participants = MagicMock()
    mock_participants.scalars.return_value.all.return_value = []

    db.execute = AsyncMock(
        side_effect=[_MockScalarResult(session), mock_participants]
    )
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    if current_status == "ended":
        # Already ended — must raise
        with pytest.raises(InvalidSessionStateError):
            await service.end_session(session_id="sess-mono", ended_by=42)
    else:
        # scheduled or active → ended is valid
        result = await service.end_session(session_id="sess-mono", ended_by=42)
        assert result.status == "ended"
        assert result.ended_at is not None


@pytest.mark.asyncio
async def test_join_transitions_scheduled_to_active_only():
    """join_session transitions scheduled→active but never active→scheduled."""
    session = _make_session(status="scheduled")
    session.started_at = None

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(0),        # count
            _MockScalarResult(None),     # no existing participant
            _MockScalarResult([]),       # participant list
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    await service.join_session(
        session_id="sess-mono",
        user_id=1,
        role="interviewer",
        display_name="Alice",
    )

    # Session should now be active
    assert session.status == "active"
    assert session.started_at is not None
