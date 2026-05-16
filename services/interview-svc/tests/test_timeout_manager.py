"""Unit tests for TimeoutManager — empty_timeout auto-end logic."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.timeout_manager import (
    EMPTY_TIMEOUT_SECONDS,
    TimeoutManager,
    _PENDING_SET_KEY,
    _timeout_key,
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    r = AsyncMock()
    r.set = AsyncMock()
    r.delete = AsyncMock()
    r.exists = AsyncMock(return_value=1)
    r.sadd = AsyncMock()
    r.srem = AsyncMock()
    r.smembers = AsyncMock(return_value=set())
    r.aclose = AsyncMock()
    return r


@pytest.fixture
def timeout_manager(mock_redis):
    """Create a TimeoutManager with a mocked Redis client."""
    return TimeoutManager(redis_client=mock_redis)


class TestTimeoutKey:
    """Tests for the _timeout_key helper."""

    def test_builds_correct_key(self):
        assert _timeout_key("abc-123") == "interview_timeout:abc-123"

    def test_key_includes_session_id(self):
        session_id = "session-xyz-456"
        key = _timeout_key(session_id)
        assert session_id in key


class TestStartTimeout:
    """Tests for starting the empty_timeout countdown."""

    @pytest.mark.asyncio
    async def test_sets_redis_key_with_ttl(self, timeout_manager, mock_redis):
        await timeout_manager.start_timeout("session-1")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "interview_timeout:session-1"
        assert call_args[1]["ex"] == EMPTY_TIMEOUT_SECONDS

    @pytest.mark.asyncio
    async def test_adds_session_to_pending_set(self, timeout_manager, mock_redis):
        await timeout_manager.start_timeout("session-1")

        mock_redis.sadd.assert_called_once_with(_PENDING_SET_KEY, "session-1")

    @pytest.mark.asyncio
    async def test_stores_iso_timestamp_as_value(self, timeout_manager, mock_redis):
        await timeout_manager.start_timeout("session-1")

        call_args = mock_redis.set.call_args
        value = call_args[0][1]
        # Should be a valid ISO timestamp
        parsed = datetime.fromisoformat(value)
        assert parsed.tzinfo is not None


class TestCancelTimeout:
    """Tests for cancelling the empty_timeout countdown."""

    @pytest.mark.asyncio
    async def test_deletes_redis_key(self, timeout_manager, mock_redis):
        await timeout_manager.cancel_timeout("session-1")

        mock_redis.delete.assert_called_once_with("interview_timeout:session-1")

    @pytest.mark.asyncio
    async def test_removes_session_from_pending_set(self, timeout_manager, mock_redis):
        await timeout_manager.cancel_timeout("session-1")

        mock_redis.srem.assert_called_once_with(_PENDING_SET_KEY, "session-1")


class TestHasPendingTimeout:
    """Tests for checking if a session has a pending timeout."""

    @pytest.mark.asyncio
    async def test_returns_true_when_key_exists(self, timeout_manager, mock_redis):
        mock_redis.exists.return_value = 1
        result = await timeout_manager.has_pending_timeout("session-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_key_missing(self, timeout_manager, mock_redis):
        mock_redis.exists.return_value = 0
        result = await timeout_manager.has_pending_timeout("session-1")
        assert result is False


class TestCheckExpiredTimeouts:
    """Tests for the expired timeout detection logic."""

    @pytest.mark.asyncio
    async def test_no_action_when_no_pending_sessions(self, timeout_manager, mock_redis):
        mock_redis.smembers.return_value = set()

        await timeout_manager._check_expired_timeouts()

        # Should not try to check any keys
        mock_redis.exists.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_end_session_when_key_still_exists(
        self, timeout_manager, mock_redis
    ):
        mock_redis.smembers.return_value = {"session-1"}
        mock_redis.exists.return_value = 1  # Key still exists (not expired)

        with patch.object(timeout_manager, "_auto_end_session", new_callable=AsyncMock) as mock_end:
            await timeout_manager._check_expired_timeouts()
            mock_end.assert_not_called()

    @pytest.mark.asyncio
    async def test_ends_session_when_key_expired(self, timeout_manager, mock_redis):
        mock_redis.smembers.return_value = {"session-1"}
        mock_redis.exists.return_value = 0  # Key expired

        with patch.object(timeout_manager, "_auto_end_session", new_callable=AsyncMock) as mock_end:
            await timeout_manager._check_expired_timeouts()
            mock_end.assert_called_once_with("session-1")

    @pytest.mark.asyncio
    async def test_removes_expired_session_from_pending_set(
        self, timeout_manager, mock_redis
    ):
        mock_redis.smembers.return_value = {"session-1"}
        mock_redis.exists.return_value = 0  # Key expired

        with patch.object(timeout_manager, "_auto_end_session", new_callable=AsyncMock):
            await timeout_manager._check_expired_timeouts()
            mock_redis.srem.assert_called_once_with(_PENDING_SET_KEY, "session-1")

    @pytest.mark.asyncio
    async def test_handles_multiple_sessions(self, timeout_manager, mock_redis):
        mock_redis.smembers.return_value = {"session-1", "session-2", "session-3"}

        # session-1 expired, session-2 still active, session-3 expired
        async def mock_exists(key):
            if "session-2" in key:
                return 1
            return 0

        mock_redis.exists = AsyncMock(side_effect=mock_exists)

        with patch.object(timeout_manager, "_auto_end_session", new_callable=AsyncMock) as mock_end:
            await timeout_manager._check_expired_timeouts()
            # Should end session-1 and session-3 but not session-2
            ended_sessions = {call[0][0] for call in mock_end.call_args_list}
            assert "session-1" in ended_sessions
            assert "session-3" in ended_sessions
            assert "session-2" not in ended_sessions


class TestAutoEndSession:
    """Tests for the auto-end session logic."""

    @pytest.mark.asyncio
    async def test_ends_active_session(self, timeout_manager):
        """Test that an active session is transitioned to ended."""
        mock_session = MagicMock()
        mock_session.status = "active"
        mock_session.room_name = "interview_abc12345"

        mock_participant = MagicMock()
        mock_participant.status = "connected"

        mock_db = AsyncMock()

        # Mock session query
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        # Mock participants query
        participants_result = MagicMock()
        participants_scalars = MagicMock()
        participants_scalars.all.return_value = [mock_participant]
        participants_result.scalars.return_value = participants_scalars

        mock_db.execute = AsyncMock(side_effect=[session_result, participants_result])
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.timeout_manager.get_async_session_factory",
            return_value=mock_session_factory,
        ), patch(
            "app.services.timeout_manager.LiveKitAdapter"
        ) as mock_livekit_cls:
            mock_livekit = AsyncMock()
            mock_livekit_cls.return_value = mock_livekit

            await timeout_manager._auto_end_session("session-1")

            assert mock_session.status == "ended"
            assert mock_session.ended_at is not None
            assert mock_participant.status == "disconnected"
            assert mock_participant.left_at is not None
            mock_livekit.delete_room.assert_called_once_with("interview_abc12345")

    @pytest.mark.asyncio
    async def test_skips_non_active_session(self, timeout_manager):
        """Test that a session not in 'active' status is skipped."""
        mock_session = MagicMock()
        mock_session.status = "ended"

        mock_db = AsyncMock()
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=session_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.timeout_manager.get_async_session_factory",
            return_value=mock_session_factory,
        ):
            await timeout_manager._auto_end_session("session-1")

            # Should not commit (no changes made)
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_missing_session(self, timeout_manager):
        """Test that a missing session is handled gracefully."""
        mock_db = AsyncMock()
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=session_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.timeout_manager.get_async_session_factory",
            return_value=mock_session_factory,
        ):
            # Should not raise
            await timeout_manager._auto_end_session("nonexistent-session")


class TestWorkerLifecycle:
    """Tests for starting and stopping the background worker."""

    @pytest.mark.asyncio
    async def test_start_worker_sets_running_flag(self, timeout_manager):
        # Start and immediately stop to avoid infinite loop
        await timeout_manager.start_worker()
        assert timeout_manager._running is True
        assert timeout_manager._task is not None
        await timeout_manager.stop_worker()

    @pytest.mark.asyncio
    async def test_stop_worker_clears_running_flag(self, timeout_manager):
        await timeout_manager.start_worker()
        await timeout_manager.stop_worker()
        assert timeout_manager._running is False
        assert timeout_manager._task is None

    @pytest.mark.asyncio
    async def test_start_worker_is_idempotent(self, timeout_manager):
        await timeout_manager.start_worker()
        task1 = timeout_manager._task
        await timeout_manager.start_worker()
        task2 = timeout_manager._task
        # Should be the same task (not started twice)
        assert task1 is task2
        await timeout_manager.stop_worker()

    @pytest.mark.asyncio
    async def test_close_stops_worker_and_closes_redis(self, timeout_manager, mock_redis):
        await timeout_manager.start_worker()
        await timeout_manager.close()
        assert timeout_manager._running is False
        mock_redis.aclose.assert_called_once()


class TestTimeoutConstants:
    """Tests for timeout configuration constants."""

    def test_empty_timeout_is_300_seconds(self):
        assert EMPTY_TIMEOUT_SECONDS == 300

    def test_timeout_key_prefix(self):
        from app.services.timeout_manager import _TIMEOUT_KEY_PREFIX
        assert _TIMEOUT_KEY_PREFIX == "interview_timeout:"
