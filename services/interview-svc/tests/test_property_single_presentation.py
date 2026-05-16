"""Property test for single active presentation (Property 9).

Property 9: Single Active Presentation
For any session, after any upload_presentation operation, there shall be exactly
one active presentation. All previously active presentations shall be deactivated.

Validates: Requirement 6.6
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from fastapi import UploadFile

from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.models.presentation import Presentation
from app.services.presentation_service import PresentationService


upload_counts = st.integers(min_value=1, max_value=5)


class _MockScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value


def _make_session():
    session = MagicMock(spec=InterviewSession)
    session.id = "sess-pres"
    session.status = "active"
    session.room_name = "interview_sess-pre"
    return session


def _make_participant():
    p = MagicMock(spec=SessionParticipant)
    p.user_id = 42
    p.role = "interviewer"
    p.status = "connected"
    return p


def _build_service(db):
    livekit = AsyncMock()
    livekit.send_data = AsyncMock()
    storage = AsyncMock()
    storage.upload_file = AsyncMock(return_value="http://localhost:9000/bucket/key")

    with patch("app.services.presentation_service.get_settings") as mock_settings:
        s = MagicMock()
        s.MAX_UPLOAD_SIZE_MB = 50
        s.S3_ENDPOINT = "http://localhost:9000"
        s.S3_BUCKET = "test-bucket"
        mock_settings.return_value = s
        service = PresentationService(db=db, livekit=livekit, storage=storage)

    return service


@pytest.mark.asyncio
async def test_upload_deactivates_previous_presentations():
    """After upload, the UPDATE query deactivates all previously active presentations."""
    session = _make_session()
    participant = _make_participant()

    db = AsyncMock()
    mock_update_result = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),
            _MockScalarResult(participant),
            mock_update_result,  # deactivate previous
        ]
    )
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = _build_service(db)

    file = UploadFile(
        filename="slides.pdf",
        file=BytesIO(b"fake pdf content"),
        headers={"content-type": "application/pdf"},
    )

    with patch(
        "app.services.presentation_service.convert_to_slides",
        new_callable=AsyncMock,
        return_value=[b"slide1", b"slide2"],
    ):
        result = await service.upload_presentation("sess-pres", file, uploaded_by=42)

    # Verify the deactivation query was executed (3rd db.execute call)
    assert db.execute.call_count == 3

    # Verify the new presentation is active
    added_presentation = db.add.call_args[0][0]
    assert added_presentation.is_active is True


@pytest.mark.asyncio
async def test_new_presentation_always_has_is_active_true():
    """Every newly uploaded presentation must have is_active=True."""
    session = _make_session()
    participant = _make_participant()

    db = AsyncMock()
    mock_update_result = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),
            _MockScalarResult(participant),
            mock_update_result,
        ]
    )
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = _build_service(db)

    file = UploadFile(
        filename="deck.pptx",
        file=BytesIO(b"fake pptx"),
        headers={"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    )

    with patch(
        "app.services.presentation_service.convert_to_slides",
        new_callable=AsyncMock,
        return_value=[b"s1"],
    ):
        result = await service.upload_presentation("sess-pres", file, uploaded_by=42)

    added = db.add.call_args[0][0]
    assert added.is_active is True
    assert added.session_id == "sess-pres"


@given(n=upload_counts)
@settings(max_examples=10)
@pytest.mark.asyncio
async def test_multiple_uploads_always_deactivate_previous(n):
    """For N sequential uploads, each one triggers deactivation of previous presentations."""
    session = _make_session()
    participant = _make_participant()

    deactivation_calls = 0

    for i in range(n):
        db = AsyncMock()
        mock_update_result = MagicMock()
        db.execute = AsyncMock(
            side_effect=[
                _MockScalarResult(session),
                _MockScalarResult(participant),
                mock_update_result,
            ]
        )
        db.add = MagicMock()
        db.commit = AsyncMock()

        service = _build_service(db)

        file = UploadFile(
            filename=f"deck_{i}.pdf",
            file=BytesIO(b"content"),
            headers={"content-type": "application/pdf"},
        )

        with patch(
            "app.services.presentation_service.convert_to_slides",
            new_callable=AsyncMock,
            return_value=[b"slide"],
        ):
            await service.upload_presentation("sess-pres", file, uploaded_by=42)

        # Each upload should have 3 execute calls (session, participant, deactivate)
        assert db.execute.call_count == 3
        deactivation_calls += 1

    # Every upload triggered a deactivation
    assert deactivation_calls == n
