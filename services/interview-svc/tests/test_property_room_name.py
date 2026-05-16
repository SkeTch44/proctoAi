"""Property test for room name convention (Property 10).

Property 10: Room Name Convention
For any created session, room_name must follow pattern `interview_{session_id[:8]}`
and be unique across all sessions.

Validates: Requirement 1.2
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.session_service import InterviewSessionService


valid_titles = st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))).filter(
    lambda s: len(s.strip()) > 0
)
valid_max_participants = st.integers(min_value=2, max_value=10)


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


@given(title=valid_titles, max_participants=valid_max_participants)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_room_name_follows_pattern(title, max_participants):
    """Room name must follow pattern interview_{session_id[:8]}."""
    service = _build_service()
    result = await service.create_session(
        creator_id=1, title=title, max_participants=max_participants
    )

    session_id = result.session_id
    expected_room_name = f"interview_{session_id[:8]}"
    assert result.room_name == expected_room_name


@given(title=valid_titles)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_room_name_starts_with_interview_prefix(title):
    """Room name always starts with 'interview_'."""
    service = _build_service()
    result = await service.create_session(creator_id=1, title=title)
    assert result.room_name.startswith("interview_")


@given(title=valid_titles)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_room_name_suffix_is_8_chars(title):
    """Room name suffix (after 'interview_') is exactly 8 characters."""
    service = _build_service()
    result = await service.create_session(creator_id=1, title=title)
    suffix = result.room_name[len("interview_"):]
    assert len(suffix) == 8


@pytest.mark.asyncio
async def test_multiple_sessions_have_unique_room_names():
    """Multiple session creations produce unique room_names (UUID-based)."""
    service = _build_service()
    room_names = set()

    for _ in range(100):
        result = await service.create_session(creator_id=1, title="Test Session")
        room_names.add(result.room_name)

    # All 100 room names should be unique
    assert len(room_names) == 100
