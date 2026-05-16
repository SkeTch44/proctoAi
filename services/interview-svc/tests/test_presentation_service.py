"""Unit tests for PresentationService.upload_presentation, get_presentation, delete_presentation, and set_current_slide."""

import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import UploadFile

from app.core.exceptions import (
    ConversionFailedError,
    FileTooLargeError,
    InvalidFileTypeError,
    InvalidSessionError,
    PermissionDeniedError,
    PresentationNotFoundError,
    SessionNotFoundError,
    SlideIndexOutOfBoundsError,
)
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.models.presentation import Presentation
from app.services.presentation_service import PresentationService


def _make_upload_file(
    filename: str = "slides.pptx",
    content: bytes = b"fake-pptx-content",
    content_type: str = "application/vnd.openxmlformats-officedocument.presentationml.presentation",
) -> UploadFile:
    """Create a mock UploadFile for testing."""
    file = UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )
    return file


def _make_session(session_id: str = "sess-1234", status: str = "active") -> MagicMock:
    """Create a mock InterviewSession."""
    session = MagicMock(spec=InterviewSession)
    session.id = session_id
    session.status = status
    session.room_name = f"interview_{session_id[:8]}"
    return session


def _make_participant(
    user_id: int = 42,
    role: str = "interviewer",
    status: str = "connected",
) -> MagicMock:
    """Create a mock SessionParticipant."""
    participant = MagicMock(spec=SessionParticipant)
    participant.user_id = user_id
    participant.role = role
    participant.status = status
    return participant


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_livekit():
    """Create a mock LiveKit adapter."""
    livekit = AsyncMock()
    livekit.send_data = AsyncMock()
    return livekit


@pytest.fixture
def mock_storage():
    """Create a mock StorageService."""
    storage = AsyncMock()
    storage.upload_file = AsyncMock(return_value="http://localhost:9000/bucket/test-key")
    storage.delete_file = AsyncMock()
    return storage


@pytest.fixture
def service(mock_db, mock_livekit, mock_storage):
    """Create a PresentationService with mocked dependencies."""
    with patch("app.services.presentation_service.get_settings") as mock_settings:
        settings = MagicMock()
        settings.MAX_UPLOAD_SIZE_MB = 50
        settings.S3_ENDPOINT = "http://localhost:9000"
        settings.S3_BUCKET = "interview-presentations"
        mock_settings.return_value = settings
        svc = PresentationService(db=mock_db, livekit=mock_livekit, storage=mock_storage)
    return svc


class TestUploadPresentationValidation:
    """Tests for validation in upload_presentation."""

    @pytest.mark.asyncio
    async def test_rejects_nonexistent_session(self, service, mock_db):
        """Session not found raises SessionNotFoundError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        file = _make_upload_file()
        with pytest.raises(SessionNotFoundError):
            await service.upload_presentation("nonexistent", file, uploaded_by=42)

    @pytest.mark.asyncio
    async def test_rejects_non_active_session(self, service, mock_db):
        """Session not in 'active' status raises InvalidSessionError."""
        session = _make_session(status="scheduled")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session
        mock_db.execute.return_value = mock_result

        file = _make_upload_file()
        with pytest.raises(InvalidSessionError):
            await service.upload_presentation("sess-1234", file, uploaded_by=42)

    @pytest.mark.asyncio
    async def test_rejects_observer_upload(self, service, mock_db):
        """Observer role raises PermissionDeniedError."""
        session = _make_session(status="active")
        participant = _make_participant(role="observer")

        # First call returns session, second returns participant
        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [mock_result_session, mock_result_participant]

        file = _make_upload_file()
        with pytest.raises(PermissionDeniedError):
            await service.upload_presentation("sess-1234", file, uploaded_by=42)

    @pytest.mark.asyncio
    async def test_rejects_non_participant_upload(self, service, mock_db):
        """Non-participant raises PermissionDeniedError."""
        session = _make_session(status="active")

        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_result_session, mock_result_participant]

        file = _make_upload_file()
        with pytest.raises(PermissionDeniedError):
            await service.upload_presentation("sess-1234", file, uploaded_by=99)

    @pytest.mark.asyncio
    async def test_rejects_invalid_extension(self, service, mock_db):
        """File with disallowed extension raises InvalidFileTypeError."""
        session = _make_session(status="active")
        participant = _make_participant(role="interviewer")

        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [mock_result_session, mock_result_participant]

        file = _make_upload_file(filename="doc.docx", content_type="application/msword")
        with pytest.raises(InvalidFileTypeError):
            await service.upload_presentation("sess-1234", file, uploaded_by=42)

    @pytest.mark.asyncio
    async def test_rejects_file_too_large(self, service, mock_db):
        """File exceeding 50MB raises FileTooLargeError."""
        session = _make_session(status="active")
        participant = _make_participant(role="interviewer")

        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [mock_result_session, mock_result_participant]

        # Create a file larger than 50MB
        large_content = b"x" * (51 * 1024 * 1024)
        file = _make_upload_file(content=large_content)
        with pytest.raises(FileTooLargeError):
            await service.upload_presentation("sess-1234", file, uploaded_by=42)


class TestUploadPresentationSuccess:
    """Tests for successful upload_presentation."""

    @pytest.mark.asyncio
    async def test_successful_upload_creates_presentation(self, service, mock_db, mock_storage, mock_livekit):
        """Successful upload stores file, converts, and creates record."""
        session = _make_session(status="active")
        participant = _make_participant(role="interviewer")

        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant
        # Third execute call is for deactivating previous presentations
        mock_result_update = MagicMock()

        mock_db.execute.side_effect = [
            mock_result_session,
            mock_result_participant,
            mock_result_update,
        ]

        # Mock the file converter to return 3 slide images
        fake_slides = [b"slide1_png", b"slide2_png", b"slide3_png"]
        with patch(
            "app.services.presentation_service.convert_to_slides",
            new_callable=AsyncMock,
            return_value=fake_slides,
        ):
            file = _make_upload_file(content=b"fake-pptx-data")
            result = await service.upload_presentation("sess-1234", file, uploaded_by=42)

        # Verify storage was called for original file + 3 slides = 4 uploads
        assert mock_storage.upload_file.call_count == 4

        # Verify presentation record was added to DB
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify LiveKit notification was sent
        mock_livekit.send_data.assert_called_once()
        call_args = mock_livekit.send_data.call_args
        data_payload = json.loads(call_args.kwargs["data"])
        assert data_payload["type"] == "presentation_loaded"
        assert data_payload["slide_count"] == 3
        assert data_payload["current_slide"] == 0

    @pytest.mark.asyncio
    async def test_interviewee_can_upload(self, service, mock_db, mock_storage, mock_livekit):
        """Interviewee role is allowed to upload presentations."""
        session = _make_session(status="active")
        participant = _make_participant(role="interviewee")

        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant
        mock_result_update = MagicMock()

        mock_db.execute.side_effect = [
            mock_result_session,
            mock_result_participant,
            mock_result_update,
        ]

        fake_slides = [b"slide1_png"]
        with patch(
            "app.services.presentation_service.convert_to_slides",
            new_callable=AsyncMock,
            return_value=fake_slides,
        ):
            file = _make_upload_file(content=b"fake-pptx-data")
            result = await service.upload_presentation("sess-1234", file, uploaded_by=101)

        mock_db.add.assert_called_once()


class TestUploadConversionFailure:
    """Tests for conversion failure handling."""

    @pytest.mark.asyncio
    async def test_conversion_timeout_raises_error(self, service, mock_db, mock_storage):
        """Conversion timeout raises ConversionFailedError."""
        import asyncio

        session = _make_session(status="active")
        participant = _make_participant(role="interviewer")

        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [mock_result_session, mock_result_participant]

        with patch(
            "app.services.presentation_service.convert_to_slides",
            new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            file = _make_upload_file(content=b"fake-pptx-data")
            with pytest.raises(ConversionFailedError, match="timed out"):
                await service.upload_presentation("sess-1234", file, uploaded_by=42)

    @pytest.mark.asyncio
    async def test_conversion_error_raises_error(self, service, mock_db, mock_storage):
        """Conversion runtime error raises ConversionFailedError."""
        session = _make_session(status="active")
        participant = _make_participant(role="interviewer")

        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [mock_result_session, mock_result_participant]

        with patch(
            "app.services.presentation_service.convert_to_slides",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LibreOffice crashed"),
        ):
            file = _make_upload_file(content=b"fake-pptx-data")
            with pytest.raises(ConversionFailedError, match="conversion failed"):
                await service.upload_presentation("sess-1234", file, uploaded_by=42)


class TestGetPresentation:
    """Tests for get_presentation."""

    @pytest.mark.asyncio
    async def test_returns_presentation_when_found(self, service, mock_db):
        """Returns the presentation record when it exists."""
        presentation = MagicMock(spec=Presentation)
        presentation.id = "pres-123"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = presentation
        mock_db.execute.return_value = mock_result

        result = await service.get_presentation("pres-123")
        assert result == presentation

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, service, mock_db):
        """Returns None when presentation does not exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_presentation("nonexistent")
        assert result is None


class TestDeletePresentation:
    """Tests for delete_presentation."""

    @pytest.mark.asyncio
    async def test_deletes_existing_presentation(self, service, mock_db, mock_storage):
        """Deletes the presentation record and associated files."""
        presentation = MagicMock(spec=Presentation)
        presentation.id = "pres-123"
        presentation.file_url = "http://localhost:9000/interview-presentations/interviews/sess/presentations/file.pptx"
        presentation.slides_json = json.dumps([
            "http://localhost:9000/interview-presentations/interviews/sess/slides/s0.png",
            "http://localhost:9000/interview-presentations/interviews/sess/slides/s1.png",
        ])

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = presentation
        mock_db.execute.return_value = mock_result

        await service.delete_presentation("pres-123")

        mock_db.delete.assert_called_once_with(presentation)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_presentation(self, service, mock_db):
        """Raises PresentationNotFoundError when presentation doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(PresentationNotFoundError):
            await service.delete_presentation("nonexistent")


def _make_presentation(
    presentation_id: str = "pres-abc",
    session_id: str = "sess-1234",
    slide_count: int = 10,
    current_slide: int = 0,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Presentation for set_current_slide tests."""
    presentation = MagicMock()
    presentation.id = presentation_id
    presentation.session_id = session_id
    presentation.slide_count = slide_count
    presentation.current_slide = current_slide
    presentation.is_active = is_active
    return presentation


class TestSetCurrentSlide:
    """Tests for set_current_slide method."""

    @pytest.mark.asyncio
    async def test_successful_slide_navigation(self, service, mock_db, mock_livekit):
        """Valid slide navigation updates DB and broadcasts change."""
        presentation = _make_presentation(slide_count=10, current_slide=0)
        participant = _make_participant(role="interviewer", user_id=42)
        session = _make_session(session_id="sess-1234", status="active")

        # Mock DB calls: 1) fetch presentation, 2) fetch participant, 3) fetch session
        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation
        mock_result_part = MagicMock()
        mock_result_part.scalar_one_or_none.return_value = participant
        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session

        mock_db.execute.side_effect = [
            mock_result_pres,
            mock_result_part,
            mock_result_session,
        ]

        result = await service.set_current_slide("pres-abc", 5, changed_by=42)

        assert result == 5
        assert presentation.current_slide == 5
        mock_db.commit.assert_called_once()

        # Verify LiveKit broadcast
        mock_livekit.send_data.assert_called_once()
        call_kwargs = mock_livekit.send_data.call_args.kwargs
        data_payload = json.loads(call_kwargs["data"])
        assert data_payload == {
            "type": "slide_change",
            "presentation_id": "pres-abc",
            "slide_index": 5,
        }
        assert call_kwargs["room_name"] == "interview_sess-123"

    @pytest.mark.asyncio
    async def test_interviewee_can_navigate(self, service, mock_db, mock_livekit):
        """Interviewee role is allowed to navigate slides."""
        presentation = _make_presentation(slide_count=5)
        participant = _make_participant(role="interviewee", user_id=101)
        session = _make_session(session_id="sess-1234")

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation
        mock_result_part = MagicMock()
        mock_result_part.scalar_one_or_none.return_value = participant
        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session

        mock_db.execute.side_effect = [
            mock_result_pres,
            mock_result_part,
            mock_result_session,
        ]

        result = await service.set_current_slide("pres-abc", 3, changed_by=101)
        assert result == 3
        assert presentation.current_slide == 3

    @pytest.mark.asyncio
    async def test_rejects_inactive_presentation(self, service, mock_db):
        """Raises PresentationNotFoundError for inactive/missing presentation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(PresentationNotFoundError):
            await service.set_current_slide("nonexistent", 0, changed_by=42)

    @pytest.mark.asyncio
    async def test_rejects_slide_index_too_high(self, service, mock_db):
        """Raises SlideIndexOutOfBoundsError when index >= slide_count."""
        presentation = _make_presentation(slide_count=5)

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation

        mock_db.execute.side_effect = [mock_result_pres]

        with pytest.raises(SlideIndexOutOfBoundsError) as exc_info:
            await service.set_current_slide("pres-abc", 5, changed_by=42)

        assert exc_info.value.slide_index == 5
        assert exc_info.value.slide_count == 5

    @pytest.mark.asyncio
    async def test_rejects_negative_slide_index(self, service, mock_db):
        """Raises SlideIndexOutOfBoundsError when index < 0."""
        presentation = _make_presentation(slide_count=5)

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation

        mock_db.execute.side_effect = [mock_result_pres]

        with pytest.raises(SlideIndexOutOfBoundsError) as exc_info:
            await service.set_current_slide("pres-abc", -1, changed_by=42)

        assert exc_info.value.slide_index == -1

    @pytest.mark.asyncio
    async def test_rejects_observer_navigation(self, service, mock_db):
        """Raises PermissionDeniedError when observer tries to navigate."""
        presentation = _make_presentation(slide_count=10)
        participant = _make_participant(role="observer", user_id=99)

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation
        mock_result_part = MagicMock()
        mock_result_part.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [mock_result_pres, mock_result_part]

        with pytest.raises(PermissionDeniedError):
            await service.set_current_slide("pres-abc", 3, changed_by=99)

    @pytest.mark.asyncio
    async def test_rejects_non_participant_navigation(self, service, mock_db):
        """Raises PermissionDeniedError when user is not a connected participant."""
        presentation = _make_presentation(slide_count=10)

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation
        mock_result_part = MagicMock()
        mock_result_part.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_result_pres, mock_result_part]

        with pytest.raises(PermissionDeniedError):
            await service.set_current_slide("pres-abc", 3, changed_by=999)

    @pytest.mark.asyncio
    async def test_navigate_to_first_slide(self, service, mock_db, mock_livekit):
        """Navigating to slide 0 (first slide) succeeds."""
        presentation = _make_presentation(slide_count=5, current_slide=3)
        participant = _make_participant(role="interviewer")
        session = _make_session()

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation
        mock_result_part = MagicMock()
        mock_result_part.scalar_one_or_none.return_value = participant
        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session

        mock_db.execute.side_effect = [
            mock_result_pres,
            mock_result_part,
            mock_result_session,
        ]

        result = await service.set_current_slide("pres-abc", 0, changed_by=42)
        assert result == 0
        assert presentation.current_slide == 0

    @pytest.mark.asyncio
    async def test_navigate_to_last_slide(self, service, mock_db, mock_livekit):
        """Navigating to slide_count-1 (last slide) succeeds."""
        presentation = _make_presentation(slide_count=10, current_slide=0)
        participant = _make_participant(role="interviewer")
        session = _make_session()

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation
        mock_result_part = MagicMock()
        mock_result_part.scalar_one_or_none.return_value = participant
        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session

        mock_db.execute.side_effect = [
            mock_result_pres,
            mock_result_part,
            mock_result_session,
        ]

        result = await service.set_current_slide("pres-abc", 9, changed_by=42)
        assert result == 9
        assert presentation.current_slide == 9

    @pytest.mark.asyncio
    async def test_broadcast_failure_does_not_fail_navigation(self, service, mock_db, mock_livekit):
        """LiveKit broadcast failure is non-fatal; slide update still succeeds."""
        presentation = _make_presentation(slide_count=5)
        participant = _make_participant(role="interviewer")
        session = _make_session()

        mock_result_pres = MagicMock()
        mock_result_pres.scalar_one_or_none.return_value = presentation
        mock_result_part = MagicMock()
        mock_result_part.scalar_one_or_none.return_value = participant
        mock_result_session = MagicMock()
        mock_result_session.scalar_one_or_none.return_value = session

        mock_db.execute.side_effect = [
            mock_result_pres,
            mock_result_part,
            mock_result_session,
        ]

        # Make LiveKit broadcast fail
        mock_livekit.send_data.side_effect = RuntimeError("LiveKit unavailable")

        result = await service.set_current_slide("pres-abc", 2, changed_by=42)

        # Navigation still succeeds
        assert result == 2
        assert presentation.current_slide == 2
        mock_db.commit.assert_called_once()
