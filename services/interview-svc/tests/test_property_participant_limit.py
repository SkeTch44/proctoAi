"""Property test for participant limit invariant (Property 1).

Property 1: Participant Limit Invariant
For any active session and any sequence of join/leave operations, the count of
connected participants shall never exceed max_participants.

Validates: Requirements 2.2, 5.3
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.exceptions import SessionFullError
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.session_service import InterviewSessionService


max_participants_strategy = st.integers(min_value=2, max_value=10)
num_join_attempts = st.integers(min_value=1, max_value=20)


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


@given(max_p=max_participants_strategy, attempts=num_join_attempts)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_join_rejected_when_at_capacity(max_p, attempts):
    """When connected count equals max_participants, join must raise SessionFullError."""
    session = MagicMock(spec=InterviewSession)
    session.id = "test-session-id"
    session.status = "active"
    session.max_participants = max_p
    session.room_name = "interview_test-ses"
    session.is_recording = False

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    # Simulate: session found, count == max_participants
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(max_p),    # count of connected participants (at capacity)
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    with pytest.raises(SessionFullError):
        await service.join_session(
            session_id="test-session-id",
            user_id=999,
            role="interviewer",
            display_name="Test User",
        )


@given(max_p=max_participants_strategy)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_join_allowed_when_below_capacity(max_p):
    """When connected count is below max_participants, join must succeed."""
    session = MagicMock(spec=InterviewSession)
    session.id = "test-session-id"
    session.status = "active"
    session.max_participants = max_p
    session.room_name = "interview_test-ses"
    session.started_at = None
    session.is_recording = False

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    current_count = max_p - 1  # One slot available

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),         # session lookup
            _MockScalarResult(current_count),   # count below capacity
            _MockScalarResult(None),            # no existing participant
            _MockScalarResult([]),              # participant list
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    result = await service.join_session(
        session_id="test-session-id",
        user_id=999,
        role="interviewer",
        display_name="Test User",
    )

    assert result.livekit_token == "token"


@given(max_p=max_participants_strategy)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_count_zero_always_allows_join(max_p):
    """When no participants are connected, join must always succeed."""
    session = MagicMock(spec=InterviewSession)
    session.id = "test-session-id"
    session.status = "active"
    session.max_participants = max_p
    session.room_name = "interview_test-ses"
    session.started_at = None
    session.is_recording = False

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(0),        # zero connected
            _MockScalarResult(None),     # no existing participant
            _MockScalarResult([]),       # participant list
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    result = await service.join_session(
        session_id="test-session-id",
        user_id=1,
        role="interviewer",
        display_name="First User",
    )

    assert result is not None
