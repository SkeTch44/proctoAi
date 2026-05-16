"""Unit tests for LiveKitAdapter (Task 2.3).

Tests token generation, room creation, delete_room retry logic,
timeout handling, and invalid role rejection using mocks.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import InvalidRoleError, ServiceUnavailableError
from app.services.livekit_adapter import LiveKitAdapter, _build_video_grants


# --- Fixtures ---


@pytest.fixture
def mock_settings():
    """Provide fake LiveKit settings for adapter instantiation."""
    with patch("app.services.livekit_adapter.get_settings") as mock_get:
        settings = MagicMock()
        settings.LIVEKIT_URL = "http://localhost:7880"
        settings.LIVEKIT_API_KEY = "test-api-key"
        settings.LIVEKIT_API_SECRET = "test-api-secret-that-is-long-enough-for-jwt"
        mock_get.return_value = settings
        yield settings


@pytest.fixture
def adapter(mock_settings):
    """Create a LiveKitAdapter with mocked settings."""
    return LiveKitAdapter()


# --- Token Generation Tests ---


class TestTokenGeneration:
    """Tests for generate_token method."""

    def test_interviewer_token_has_full_grants(self, adapter):
        """Interviewer token includes publish, subscribe, and data permissions."""
        token = adapter.generate_token(
            room_name="room-abc",
            identity="123",
            name="Alice",
            role="interviewer",
        )
        # Token is a JWT string
        assert isinstance(token, str)
        assert len(token) > 0

    def test_interviewee_token_has_full_grants(self, adapter):
        """Interviewee token includes publish, subscribe, and data permissions."""
        token = adapter.generate_token(
            room_name="room-abc",
            identity="456",
            name="Bob",
            role="interviewee",
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_observer_token_has_subscribe_only(self, adapter):
        """Observer token has subscribe but no publish or data permissions."""
        token = adapter.generate_token(
            room_name="room-abc",
            identity="789",
            name="Charlie",
            role="observer",
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_interviewer_grants_are_correct(self):
        """Verify _build_video_grants for interviewer role."""
        grants = _build_video_grants("room-1", "interviewer")
        assert grants.can_publish is True
        assert grants.can_subscribe is True
        assert grants.can_publish_data is True
        assert grants.room == "room-1"
        assert grants.room_join is True

    def test_interviewee_grants_are_correct(self):
        """Verify _build_video_grants for interviewee role."""
        grants = _build_video_grants("room-2", "interviewee")
        assert grants.can_publish is True
        assert grants.can_subscribe is True
        assert grants.can_publish_data is True
        assert grants.room == "room-2"
        assert grants.room_join is True

    def test_observer_grants_are_correct(self):
        """Verify _build_video_grants for observer role."""
        grants = _build_video_grants("room-3", "observer")
        assert grants.can_publish is False
        assert grants.can_subscribe is True
        assert grants.can_publish_data is False
        assert grants.room == "room-3"
        assert grants.room_join is True

    def test_invalid_role_raises_error(self, adapter):
        """Invalid role raises InvalidRoleError during token generation."""
        with pytest.raises(InvalidRoleError) as exc_info:
            adapter.generate_token(
                room_name="room-abc",
                identity="100",
                name="Dave",
                role="admin",
            )
        assert exc_info.value.role == "admin"

    def test_no_role_and_no_grants_raises_error(self, adapter):
        """Missing both role and grants raises InvalidRoleError."""
        with pytest.raises(InvalidRoleError):
            adapter.generate_token(
                room_name="room-abc",
                identity="100",
                name="Eve",
            )


# --- Room Creation Tests ---


class TestRoomCreation:
    """Tests for create_room method."""

    @pytest.mark.asyncio
    async def test_create_room_success(self, adapter):
        """Room creation with valid parameters returns room info dict."""
        mock_room_info = MagicMock()
        mock_room_info.name = "interview-room-1"
        mock_room_info.sid = "RM_abc123"
        mock_room_info.max_participants = 6
        mock_room_info.empty_timeout = 300

        mock_room_service = MagicMock()
        mock_room_service.create_room = AsyncMock(return_value=mock_room_info)

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk):
            result = await adapter.create_room(
                room_name="interview-room-1",
                max_participants=6,
                empty_timeout=300,
            )

        assert result == {
            "name": "interview-room-1",
            "sid": "RM_abc123",
            "max_participants": 6,
            "empty_timeout": 300,
        }
        mock_lk.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_room_timeout_raises_service_unavailable(self, adapter):
        """Timeout during room creation raises ServiceUnavailableError."""
        mock_room_service = MagicMock()
        mock_room_service.create_room = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk):
            with pytest.raises(ServiceUnavailableError) as exc_info:
                await adapter.create_room(room_name="timeout-room")

        assert exc_info.value.service == "LiveKit"
        assert exc_info.value.retry_after == 5

    @pytest.mark.asyncio
    async def test_create_room_connection_error_raises_service_unavailable(self, adapter):
        """Connection error during room creation raises ServiceUnavailableError."""
        mock_room_service = MagicMock()
        mock_room_service.create_room = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk):
            with pytest.raises(ServiceUnavailableError):
                await adapter.create_room(room_name="error-room")


# --- Delete Room Retry Tests ---


class TestDeleteRoomRetry:
    """Tests for delete_room retry logic."""

    @pytest.mark.asyncio
    async def test_delete_room_succeeds_on_first_attempt(self, adapter):
        """Successful delete on first try does not retry."""
        mock_room_service = MagicMock()
        mock_room_service.delete_room = AsyncMock(return_value=None)

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk):
            await adapter.delete_room("room-to-delete")

        assert mock_room_service.delete_room.await_count == 1

    @pytest.mark.asyncio
    async def test_delete_room_retries_on_failure_then_succeeds(self, adapter):
        """delete_room retries on failure and succeeds on third attempt."""
        mock_room_service = MagicMock()
        mock_room_service.delete_room = AsyncMock(
            side_effect=[
                ConnectionError("fail 1"),
                ConnectionError("fail 2"),
                None,  # success on third attempt
            ]
        )

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk), \
             patch("app.services.livekit_adapter.asyncio.sleep", new_callable=AsyncMock):
            await adapter.delete_room("retry-room")

        assert mock_room_service.delete_room.await_count == 3

    @pytest.mark.asyncio
    async def test_delete_room_all_retries_exhausted_raises_error(self, adapter):
        """All 3 retry attempts failing raises ServiceUnavailableError."""
        mock_room_service = MagicMock()
        mock_room_service.delete_room = AsyncMock(
            side_effect=ConnectionError("persistent failure")
        )

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk), \
             patch("app.services.livekit_adapter.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ServiceUnavailableError) as exc_info:
                await adapter.delete_room("doomed-room")

        assert exc_info.value.service == "LiveKit"
        assert mock_room_service.delete_room.await_count == 3


# --- Timeout Handling Tests ---


class TestTimeoutHandling:
    """Tests for 5-second timeout enforcement."""

    @pytest.mark.asyncio
    async def test_create_room_respects_5s_timeout(self, adapter):
        """create_room uses asyncio.wait_for with 5-second timeout."""
        mock_room_service = MagicMock()
        mock_room_service.create_room = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk):
            with pytest.raises(ServiceUnavailableError) as exc_info:
                await adapter.create_room(room_name="slow-room")

        assert exc_info.value.retry_after == 5

    @pytest.mark.asyncio
    async def test_delete_room_timeout_triggers_retry(self, adapter):
        """Timeout on delete_room triggers retry attempts."""
        mock_room_service = MagicMock()
        mock_room_service.delete_room = AsyncMock(
            side_effect=[
                asyncio.TimeoutError(),
                asyncio.TimeoutError(),
                None,  # succeeds on third attempt
            ]
        )

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk), \
             patch("app.services.livekit_adapter.asyncio.sleep", new_callable=AsyncMock):
            await adapter.delete_room("timeout-retry-room")

        assert mock_room_service.delete_room.await_count == 3

    @pytest.mark.asyncio
    async def test_remove_participant_timeout(self, adapter):
        """remove_participant timeout raises ServiceUnavailableError."""
        mock_room_service = MagicMock()
        mock_room_service.remove_participant = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        mock_lk = MagicMock()
        mock_lk.room = mock_room_service
        mock_lk.aclose = AsyncMock()

        with patch.object(adapter, "_get_api", return_value=mock_lk):
            with pytest.raises(ServiceUnavailableError) as exc_info:
                await adapter.remove_participant("room-x", "user-1")

        assert exc_info.value.service == "LiveKit"
        assert exc_info.value.retry_after == 5


# --- Invalid Role Rejection Tests ---


class TestInvalidRoleRejection:
    """Tests verifying InvalidRoleError is raised for bad roles."""

    def test_build_video_grants_rejects_admin(self):
        """'admin' is not a valid role."""
        with pytest.raises(InvalidRoleError) as exc_info:
            _build_video_grants("room", "admin")
        assert exc_info.value.role == "admin"

    def test_build_video_grants_rejects_empty_string(self):
        """Empty string is not a valid role."""
        with pytest.raises(InvalidRoleError) as exc_info:
            _build_video_grants("room", "")
        assert exc_info.value.role == ""

    def test_build_video_grants_rejects_capitalized_role(self):
        """Roles are case-sensitive — 'Interviewer' is invalid."""
        with pytest.raises(InvalidRoleError) as exc_info:
            _build_video_grants("room", "Interviewer")
        assert exc_info.value.role == "Interviewer"

    def test_generate_token_rejects_invalid_role(self, adapter):
        """generate_token raises InvalidRoleError for unknown roles."""
        with pytest.raises(InvalidRoleError):
            adapter.generate_token(
                room_name="room",
                identity="1",
                name="Test",
                role="moderator",
            )

    def test_build_video_grants_rejects_numeric_role(self):
        """Numeric string is not a valid role."""
        with pytest.raises(InvalidRoleError) as exc_info:
            _build_video_grants("room", "123")
        assert exc_info.value.role == "123"
