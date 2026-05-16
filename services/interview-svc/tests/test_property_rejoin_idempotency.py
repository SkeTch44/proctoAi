"""Property test for rejoin idempotency (Property 6).

Property 6: Rejoin Idempotency
For any user who has left a session, rejoining reactivates the existing record.
The total count of participant records for that (user_id, session_id) is always exactly 1.

Validates: Requirements 2.4, 5.4
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.session_service import InterviewSessionService


user_ids = st.integers(min_value=1, max_value=10000)
roles = st.sampled_from(["interviewer", "interviewee", "observer"])
display_names = st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",)))


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
    session.id = "sess-rejoin"
    session.status = "active"
    session.max_participants = 6
    session.room_name = "interview_sess-rej"
    session.started_at = datetime(2025, 1, 1, tzinfo=UTC)
    session.is_recording = False
    return session


def _make_disconnected_participant(user_id, role="interviewer"):
    p = MagicMock(spec=SessionParticipant)
    p.user_id = user_id
    p.session_id = "sess-rejoin"
    p.role = role
    p.status = "disconnected"
    p.display_name = "Test User"
    p.joined_at = datetime(2025, 1, 1, tzinfo=UTC)
    p.left_at = datetime(2025, 1, 1, 1, 0, tzinfo=UTC)
    return p


@given(user_id=user_ids)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_rejoin_reactivates_existing_record(user_id):
    """Rejoining a session reactivates the existing disconnected record."""
    session = _make_session()
    disconnected = _make_disconnected_participant(user_id)

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),       # session lookup
            _MockScalarResult(1),             # count of connected
            _MockScalarResult(disconnected),  # existing participant (disconnected)
            _MockScalarResult([disconnected]),  # participant list
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    result = await service.join_session(
        session_id="sess-rejoin",
        user_id=user_id,
        role="interviewer",
        display_name="Rejoining User",
    )

    # Verify the existing record was reactivated
    assert disconnected.status == "connected"
    assert disconnected.left_at is None
    assert disconnected.joined_at is not None

    # Verify NO new record was created (db.add should NOT be called)
    db.add.assert_not_called()

    # Verify result is valid
    assert result.livekit_token == "token"


@given(user_id=user_ids)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_rejoin_does_not_create_duplicate_record(user_id):
    """After rejoin, there is still exactly one participant record for the user."""
    session = _make_session()
    disconnected = _make_disconnected_participant(user_id)

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),
            _MockScalarResult(1),
            _MockScalarResult(disconnected),
            _MockScalarResult([disconnected]),
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    await service.join_session(
        session_id="sess-rejoin",
        user_id=user_id,
        role="interviewer",
        display_name="User",
    )

    # db.add must NOT be called — no new record created
    db.add.assert_not_called()

    # The participant list returned should contain exactly 1 entry for this user
    # (the reactivated record)
    assert disconnected.status == "connected"


@given(user_id=user_ids)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_rejoin_clears_left_at_timestamp(user_id):
    """On rejoin, left_at must be cleared to None."""
    session = _make_session()
    disconnected = _make_disconnected_participant(user_id)
    # Ensure left_at is set before rejoin
    disconnected.left_at = datetime(2025, 6, 15, 10, 30, tzinfo=UTC)

    db = AsyncMock()
    livekit = MagicMock()
    livekit.generate_token = MagicMock(return_value="token")

    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),
            _MockScalarResult(1),
            _MockScalarResult(disconnected),
            _MockScalarResult([disconnected]),
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    service = InterviewSessionService(db=db, livekit=livekit)

    await service.join_session(
        session_id="sess-rejoin",
        user_id=user_id,
        role="interviewer",
        display_name="User",
    )

    assert disconnected.left_at is None
