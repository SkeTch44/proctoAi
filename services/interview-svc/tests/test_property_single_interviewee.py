"""Property test for single interviewee constraint (Property 2).

Property 2: Single Interviewee Constraint
For any session and any sequence of join operations, the count of connected
interviewees shall never exceed 1.

Validates: Requirement 2.3
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.exceptions import DuplicateIntervieweeError
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.session_service import InterviewSessionService


user_ids = st.integers(min_value=1, max_value=10000)


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


def _make_session():
    session = MagicMock(spec=InterviewSession)
    session.id = "sess-123"
    session.status = "active"
    session.max_participants = 6
    session.room_name = "interview_sess-123"
    session.started_at = None
    session.is_recording = False
    return session


@given(user_id=user_ids)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_second_interviewee_always_rejected(user_id):
    """When a connected interviewee exists, any new interviewee join must be rejected."""
    session = _make_session()
    existing_interviewee = MagicMock(spec=SessionParticipant)
    existing_interviewee.role = "interviewee"
    existing_interviewee.status = "connected"

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),              # session lookup
            _MockScalarResult(1),                    # count of connected (below max)
            _MockScalarResult(existing_interviewee), # existing interviewee found
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    with pytest.raises(DuplicateIntervieweeError):
        await service.join_session(
            session_id="sess-123",
            user_id=user_id,
            role="interviewee",
            display_name="Candidate",
        )


@given(user_id=user_ids)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_first_interviewee_always_allowed(user_id):
    """When no connected interviewee exists, the first interviewee join must succeed."""
    session = _make_session()

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(0),        # count of connected
            _MockScalarResult(None),     # no existing interviewee
            _MockScalarResult(None),     # no existing participant for this user
            _MockScalarResult([]),       # participant list
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    result = await service.join_session(
        session_id="sess-123",
        user_id=user_id,
        role="interviewee",
        display_name="Candidate",
    )

    assert result.livekit_token == "token"


@given(user_id=user_ids)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_interviewer_join_unaffected_by_interviewee_constraint(user_id):
    """Interviewer joins should never trigger the interviewee constraint check."""
    session = _make_session()

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    # Note: no interviewee check query in the sequence for interviewer role
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),  # session lookup
            _MockScalarResult(1),        # count of connected
            _MockScalarResult(None),     # no existing participant for this user
            _MockScalarResult([]),       # participant list
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    result = await service.join_session(
        session_id="sess-123",
        user_id=user_id,
        role="interviewer",
        display_name="Interviewer",
    )

    assert result is not None
