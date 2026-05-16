"""Property test for slide index bounds (Property 5).

Property 5: Slide Index Bounds
For any active presentation and any sequence of set_current_slide operations
(including rejected out-of-bounds attempts), current_slide always satisfies
0 <= current_slide < slide_count.

Validates: Requirements 7.2, 7.3
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.core.exceptions import PresentationNotFoundError
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.models.presentation import Presentation
from app.services.presentation_service import PresentationService


slide_counts = st.integers(min_value=1, max_value=100)
valid_indices = st.integers(min_value=0, max_value=99)
negative_indices = st.integers(min_value=-1000, max_value=-1)


class _MockScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value


def _make_presentation(slide_count=10, current_slide=0):
    p = MagicMock(spec=Presentation)
    p.id = "pres-bounds"
    p.session_id = "sess-bounds"
    p.slide_count = slide_count
    p.current_slide = current_slide
    p.is_active = True
    return p


def _make_participant(role="interviewer"):
    part = MagicMock(spec=SessionParticipant)
    part.user_id = 42
    part.role = role
    part.status = "connected"
    return part


def _make_session():
    s = MagicMock(spec=InterviewSession)
    s.id = "sess-bounds"
    s.room_name = "interview_sess-bou"
    return s


def _build_service(db):
    livekit = AsyncMock()
    livekit.send_data = AsyncMock()

    with patch("app.services.presentation_service.get_settings") as mock_settings:
        s = MagicMock()
        s.MAX_UPLOAD_SIZE_MB = 50
        s.S3_ENDPOINT = "http://localhost:9000"
        s.S3_BUCKET = "test-bucket"
        mock_settings.return_value = s
        service = PresentationService(db=db, livekit=livekit)

    return service


@given(slide_count=slide_counts, slide_index=valid_indices)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_valid_index_within_bounds_succeeds(slide_count, slide_index):
    """Any slide_index in [0, slide_count-1] must succeed."""
    assume(slide_index < slide_count)

    presentation = _make_presentation(slide_count=slide_count)
    participant = _make_participant()
    session = _make_session()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(presentation),  # presentation lookup
            _MockScalarResult(participant),    # participant lookup
            _MockScalarResult(session),        # session lookup for broadcast
        ]
    )
    db.commit = AsyncMock()

    service = _build_service(db)

    result = await service.set_current_slide(
        presentation_id="pres-bounds",
        slide_index=slide_index,
        changed_by=42,
    )

    assert result == slide_index
    assert 0 <= result < slide_count


@given(slide_count=slide_counts, slide_index=valid_indices)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_index_at_or_above_slide_count_rejected(slide_count, slide_index):
    """Any slide_index >= slide_count must be rejected."""
    assume(slide_index >= slide_count)

    presentation = _make_presentation(slide_count=slide_count)
    participant = _make_participant()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(presentation),
            _MockScalarResult(participant),
        ]
    )
    db.commit = AsyncMock()

    service = _build_service(db)

    with pytest.raises(ValueError, match="out of bounds"):
        await service.set_current_slide(
            presentation_id="pres-bounds",
            slide_index=slide_index,
            changed_by=42,
        )

    # current_slide should remain unchanged
    assert presentation.current_slide == 0


@given(slide_index=negative_indices)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_negative_index_always_rejected(slide_index):
    """Negative slide indices must always be rejected."""
    presentation = _make_presentation(slide_count=10)
    participant = _make_participant()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(presentation),
            _MockScalarResult(participant),
        ]
    )
    db.commit = AsyncMock()

    service = _build_service(db)

    with pytest.raises(ValueError, match="out of bounds"):
        await service.set_current_slide(
            presentation_id="pres-bounds",
            slide_index=slide_index,
            changed_by=42,
        )


@given(slide_count=slide_counts)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_boundary_index_slide_count_minus_one_succeeds(slide_count):
    """slide_index == slide_count - 1 (last slide) must always succeed."""
    last_index = slide_count - 1
    presentation = _make_presentation(slide_count=slide_count)
    participant = _make_participant()
    session = _make_session()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(presentation),
            _MockScalarResult(participant),
            _MockScalarResult(session),
        ]
    )
    db.commit = AsyncMock()

    service = _build_service(db)

    result = await service.set_current_slide(
        presentation_id="pres-bounds",
        slide_index=last_index,
        changed_by=42,
    )

    assert result == last_index


@given(slide_count=slide_counts)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_index_zero_always_succeeds(slide_count):
    """slide_index == 0 (first slide) must always succeed for any slide_count >= 1."""
    presentation = _make_presentation(slide_count=slide_count)
    participant = _make_participant()
    session = _make_session()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(presentation),
            _MockScalarResult(participant),
            _MockScalarResult(session),
        ]
    )
    db.commit = AsyncMock()

    service = _build_service(db)

    result = await service.set_current_slide(
        presentation_id="pres-bounds",
        slide_index=0,
        changed_by=42,
    )

    assert result == 0
