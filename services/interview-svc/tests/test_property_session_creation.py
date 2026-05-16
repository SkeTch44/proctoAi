"""Property test for session creation validation (Property 7).

Property 7: Session Creation Validation
For any title that is empty or exceeds 500 chars, or max_participants outside [2, 10],
creation must be rejected. For valid inputs (1-500 char title, 2-10 max_participants),
creation must succeed.

Validates: Requirements 1.3, 1.4
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.services.session_service import InterviewSessionService, SessionValidationError


# Strategies
valid_titles = st.text(min_size=1, max_size=500, alphabet=st.characters(blacklist_categories=("Cs",))).filter(
    lambda s: len(s.strip()) > 0
)
invalid_titles_empty = st.just("")
invalid_titles_whitespace = st.text(alphabet=" \t\n\r", min_size=1, max_size=10)
invalid_titles_too_long = st.text(min_size=501, max_size=600, alphabet=st.characters(blacklist_categories=("Cs",)))

valid_max_participants = st.integers(min_value=2, max_value=10)
invalid_max_participants_low = st.integers(min_value=-100, max_value=1)
invalid_max_participants_high = st.integers(min_value=11, max_value=1000)


def _build_service():
    """Build a service with mocked dependencies."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    livekit = AsyncMock()
    livekit.create_room = AsyncMock(return_value={"name": "test_room"})

    return InterviewSessionService(db=db, livekit=livekit)


@given(title=invalid_titles_empty)
@settings(max_examples=10)
@pytest.mark.asyncio
async def test_empty_title_rejected(title):
    """Empty title must be rejected."""
    service = _build_service()
    with pytest.raises(SessionValidationError, match="empty"):
        await service.create_session(creator_id=1, title=title, max_participants=6)


@given(title=invalid_titles_whitespace)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_whitespace_only_title_rejected(title):
    """Whitespace-only title must be rejected."""
    service = _build_service()
    with pytest.raises(SessionValidationError, match="empty"):
        await service.create_session(creator_id=1, title=title, max_participants=6)


@given(title=invalid_titles_too_long)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_title_exceeding_500_chars_rejected(title):
    """Title exceeding 500 characters must be rejected."""
    assume(len(title) > 500)
    service = _build_service()
    with pytest.raises(SessionValidationError, match="500"):
        await service.create_session(creator_id=1, title=title, max_participants=6)


@given(max_participants=invalid_max_participants_low)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_max_participants_below_2_rejected(max_participants):
    """max_participants below 2 must be rejected."""
    service = _build_service()
    with pytest.raises(SessionValidationError, match="between 2 and 10"):
        await service.create_session(
            creator_id=1, title="Valid Title", max_participants=max_participants
        )


@given(max_participants=invalid_max_participants_high)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_max_participants_above_10_rejected(max_participants):
    """max_participants above 10 must be rejected."""
    service = _build_service()
    with pytest.raises(SessionValidationError, match="between 2 and 10"):
        await service.create_session(
            creator_id=1, title="Valid Title", max_participants=max_participants
        )


@given(title=valid_titles, max_participants=valid_max_participants)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_valid_inputs_succeed(title, max_participants):
    """Valid title (1-500 chars) and max_participants (2-10) must succeed."""
    service = _build_service()
    result = await service.create_session(
        creator_id=1, title=title, max_participants=max_participants
    )
    assert result.session_id is not None
    assert result.room_name.startswith("interview_")
    assert result.join_url is not None
