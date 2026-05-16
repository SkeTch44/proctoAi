"""Unit tests for InterviewSessionService.create_session."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.session_service import (
    CreateSessionResult,
    InterviewSessionService,
    LiveKitUnavailableError,
    SessionValidationError,
)


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_livekit():
    """Create a mock LiveKit adapter."""
    livekit = AsyncMock()
    livekit.create_room = AsyncMock(return_value={"name": "test_room"})
    return livekit


@pytest.fixture
def service(mock_db, mock_livekit):
    """Create an InterviewSessionService with mocked dependencies."""
    return InterviewSessionService(db=mock_db, livekit=mock_livekit)


class TestCreateSessionValidation:
    """Tests for input validation in create_session."""

    @pytest.mark.asyncio
    async def test_rejects_empty_title(self, service):
        with pytest.raises(SessionValidationError, match="Title must not be empty"):
            await service.create_session(creator_id=1, title="")

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_title(self, service):
        with pytest.raises(SessionValidationError, match="Title must not be empty"):
            await service.create_session(creator_id=1, title="   ")

    @pytest.mark.asyncio
    async def test_rejects_title_exceeding_500_chars(self, service):
        long_title = "x" * 501
        with pytest.raises(SessionValidationError, match="must not exceed 500 characters"):
            await service.create_session(creator_id=1, title=long_title)

    @pytest.mark.asyncio
    async def test_rejects_max_participants_below_2(self, service):
        with pytest.raises(SessionValidationError, match="must be between 2 and 10"):
            await service.create_session(
                creator_id=1, title="Valid Title", max_participants=1
            )

    @pytest.mark.asyncio
    async def test_rejects_max_participants_above_10(self, service):
        with pytest.raises(SessionValidationError, match="must be between 2 and 10"):
            await service.create_session(
                creator_id=1, title="Valid Title", max_participants=11
            )


class TestCreateSessionSuccess:
    """Tests for successful session creation."""

    @pytest.mark.asyncio
    async def test_returns_create_session_result(self, service):
        result = await service.create_session(
            creator_id=42,
            title="Backend Interview",
            max_participants=4,
        )
        assert isinstance(result, CreateSessionResult)
        assert result.session_id is not None
        assert result.room_name.startswith("interview_")
        assert result.room_name == f"interview_{result.session_id[:8]}"
        assert result.join_url == f"/api/v1/interviews/sessions/{result.session_id}/join"

    @pytest.mark.asyncio
    async def test_persists_session_to_db(self, service, mock_db):
        await service.create_session(creator_id=42, title="Test Session")
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_livekit_room_with_correct_params(self, service, mock_livekit):
        result = await service.create_session(
            creator_id=42,
            title="Test Session",
            max_participants=5,
        )
        mock_livekit.create_room.assert_called_once_with(
            room_name=result.room_name,
            max_participants=5,
            empty_timeout=300,
        )

    @pytest.mark.asyncio
    async def test_session_has_scheduled_status(self, service, mock_db):
        await service.create_session(creator_id=42, title="Test Session")
        session_arg = mock_db.add.call_args[0][0]
        assert session_arg.status == "scheduled"

    @pytest.mark.asyncio
    async def test_session_stores_creator_id(self, service, mock_db):
        await service.create_session(creator_id=99, title="Test Session")
        session_arg = mock_db.add.call_args[0][0]
        assert session_arg.creator_id == 99

    @pytest.mark.asyncio
    async def test_session_stores_scheduled_at(self, service, mock_db):
        scheduled = datetime(2025, 8, 1, 14, 0)
        await service.create_session(
            creator_id=1, title="Scheduled", scheduled_at=scheduled
        )
        session_arg = mock_db.add.call_args[0][0]
        assert session_arg.scheduled_at == scheduled

    @pytest.mark.asyncio
    async def test_default_max_participants_is_6(self, service, mock_db):
        await service.create_session(creator_id=1, title="Default Params")
        session_arg = mock_db.add.call_args[0][0]
        assert session_arg.max_participants == 6

    @pytest.mark.asyncio
    async def test_accepts_title_at_boundary_500_chars(self, service):
        title = "x" * 500
        result = await service.create_session(creator_id=1, title=title)
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_accepts_min_max_participants_2(self, service, mock_livekit):
        result = await service.create_session(
            creator_id=1, title="Small", max_participants=2
        )
        mock_livekit.create_room.assert_called_once_with(
            room_name=result.room_name,
            max_participants=2,
            empty_timeout=300,
        )

    @pytest.mark.asyncio
    async def test_accepts_max_max_participants_10(self, service, mock_livekit):
        result = await service.create_session(
            creator_id=1, title="Large", max_participants=10
        )
        mock_livekit.create_room.assert_called_once_with(
            room_name=result.room_name,
            max_participants=10,
            empty_timeout=300,
        )


class TestCreateSessionLiveKitFailure:
    """Tests for LiveKit failure handling during session creation."""

    @pytest.mark.asyncio
    async def test_rolls_back_db_on_livekit_failure(self, mock_db, mock_livekit):
        mock_livekit.create_room = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        service = InterviewSessionService(db=mock_db, livekit=mock_livekit)

        with pytest.raises(LiveKitUnavailableError):
            await service.create_session(creator_id=1, title="Will Fail")

        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_livekit_unavailable_error(self, mock_db, mock_livekit):
        mock_livekit.create_room = AsyncMock(
            side_effect=TimeoutError("Timed out")
        )
        service = InterviewSessionService(db=mock_db, livekit=mock_livekit)

        with pytest.raises(LiveKitUnavailableError, match="Failed to create LiveKit room"):
            await service.create_session(creator_id=1, title="Timeout Test")

    @pytest.mark.asyncio
    async def test_does_not_persist_session_on_livekit_failure(self, mock_db, mock_livekit):
        mock_livekit.create_room = AsyncMock(
            side_effect=RuntimeError("Server error")
        )
        service = InterviewSessionService(db=mock_db, livekit=mock_livekit)

        with pytest.raises(LiveKitUnavailableError):
            await service.create_session(creator_id=1, title="No Persist")

        # commit should never be called when LiveKit fails
        mock_db.commit.assert_not_called()
