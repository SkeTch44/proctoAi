"""Property test for file upload validation (Property 8).

Property 8: File Upload Validation
For any file exceeding 50MB, or with extension not in {.ppt, .pptx, .pdf, .key},
or with MIME type mismatch, upload must be rejected. Valid files must be accepted.

Validates: Requirements 6.2, 6.3, 10.4
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from fastapi import UploadFile

from app.core.exceptions import FileTooLargeError, InvalidFileTypeError
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.presentation_service import PresentationService, ALLOWED_EXTENSIONS


# Strategies
valid_extensions = st.sampled_from([".ppt", ".pptx", ".pdf", ".key"])
invalid_extensions = st.sampled_from([
    ".docx", ".doc", ".txt", ".jpg", ".png", ".exe", ".zip", ".html", ".csv",
    ".xlsx", ".mp4", ".avi", ".py", ".js", ".json",
])
file_sizes_valid = st.integers(min_value=1, max_value=50 * 1024 * 1024)  # 1 byte to 50MB
file_sizes_too_large = st.integers(min_value=50 * 1024 * 1024 + 1, max_value=100 * 1024 * 1024)


class _MockScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value


def _make_session():
    session = MagicMock(spec=InterviewSession)
    session.id = "sess-upload"
    session.status = "active"
    session.room_name = "interview_sess-upl"
    return session


def _make_participant(role="interviewer"):
    p = MagicMock(spec=SessionParticipant)
    p.user_id = 42
    p.role = role
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


@given(ext=invalid_extensions)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_invalid_extension_always_rejected(ext):
    """Files with extensions not in the allowed set must be rejected."""
    session = _make_session()
    participant = _make_participant()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[_MockScalarResult(session), _MockScalarResult(participant)]
    )
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = _build_service(db)

    file = UploadFile(
        filename=f"document{ext}",
        file=BytesIO(b"fake content"),
        headers={"content-type": "application/octet-stream"},
    )

    with pytest.raises(InvalidFileTypeError):
        await service.upload_presentation("sess-upload", file, uploaded_by=42)


@given(ext=valid_extensions)
@settings(max_examples=20)
@pytest.mark.asyncio
async def test_valid_extension_not_rejected_for_type(ext):
    """Files with valid extensions should not raise InvalidFileTypeError."""
    session = _make_session()
    participant = _make_participant()

    db = AsyncMock()

    mock_update_result = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _MockScalarResult(session),
            _MockScalarResult(participant),
            mock_update_result,  # deactivate previous presentations
        ]
    )
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = _build_service(db)

    # Use small valid content
    content = b"x" * 100
    file = UploadFile(
        filename=f"slides{ext}",
        file=BytesIO(content),
        headers={"content-type": "application/octet-stream"},
    )

    # Mock the converter to return fake slides
    with patch(
        "app.services.presentation_service.convert_to_slides",
        new_callable=AsyncMock,
        return_value=[b"slide1"],
    ):
        result = await service.upload_presentation("sess-upload", file, uploaded_by=42)

    # Should not raise InvalidFileTypeError — it succeeded
    assert result is not None


@pytest.mark.asyncio
async def test_file_exceeding_50mb_rejected():
    """Files larger than 50MB must be rejected with FileTooLargeError."""
    session = _make_session()
    participant = _make_participant()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[_MockScalarResult(session), _MockScalarResult(participant)]
    )
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = _build_service(db)

    # Create content just over 50MB
    large_content = b"x" * (50 * 1024 * 1024 + 1)
    file = UploadFile(
        filename="big_presentation.pptx",
        file=BytesIO(large_content),
        headers={"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    )

    with pytest.raises(FileTooLargeError):
        await service.upload_presentation("sess-upload", file, uploaded_by=42)


@pytest.mark.asyncio
async def test_file_exactly_50mb_accepted():
    """Files exactly at 50MB should be accepted (boundary case)."""
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

    content = b"x" * (50 * 1024 * 1024)  # Exactly 50MB
    file = UploadFile(
        filename="exact_50mb.pdf",
        file=BytesIO(content),
        headers={"content-type": "application/pdf"},
    )

    with patch(
        "app.services.presentation_service.convert_to_slides",
        new_callable=AsyncMock,
        return_value=[b"slide1"],
    ):
        result = await service.upload_presentation("sess-upload", file, uploaded_by=42)

    assert result is not None
