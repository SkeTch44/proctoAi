"""Timeout manager — handles empty_timeout auto-end logic for interview sessions.

When all interviewers disconnect from an active session, a 5-minute (300s) countdown
starts. If no interviewer rejoins within that window, the session is automatically ended
and the LiveKit room is deleted.

Implementation uses Redis for timeout tracking:
- Set key `interview_timeout:{session_id}` with TTL=300 when last interviewer leaves
- Delete the key when an interviewer rejoins (cancels the countdown)
- A background asyncio task polls for expired timeouts and ends sessions
"""

import asyncio
import logging
from datetime import UTC, datetime

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session_factory
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.livekit_adapter import LiveKitAdapter

logger = logging.getLogger(__name__)

# Redis key prefix for timeout tracking
_TIMEOUT_KEY_PREFIX = "interview_timeout:"

# Set that tracks which sessions have a pending timeout
_PENDING_SET_KEY = "interview_timeouts_pending"

# Timeout duration in seconds (5 minutes)
EMPTY_TIMEOUT_SECONDS = 300

# Polling interval for the background worker (seconds)
_POLL_INTERVAL = 10


def _timeout_key(session_id: str) -> str:
    """Build the Redis key for a session timeout."""
    return f"{_TIMEOUT_KEY_PREFIX}{session_id}"


class TimeoutManager:
    """Manages empty_timeout auto-end logic for interview sessions.

    Uses Redis to track countdown state and a background asyncio task
    to detect expired timeouts and end sessions.
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        self._redis: redis.Redis | None = redis_client
        self._task: asyncio.Task | None = None
        self._running = False

    async def _get_redis(self) -> redis.Redis:
        """Lazily initialize the Redis connection."""
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return self._redis

    async def start_timeout(self, session_id: str) -> None:
        """Start the empty_timeout countdown for a session.

        Called when the last interviewer disconnects from an active session.
        Sets a Redis key with TTL=300 and adds the session to the pending set.

        Args:
            session_id: The session that lost all interviewers.
        """
        r = await self._get_redis()
        key = _timeout_key(session_id)

        # Set the timeout key with TTL — value is the timestamp when timeout was started
        await r.set(key, datetime.now(UTC).isoformat(), ex=EMPTY_TIMEOUT_SECONDS)

        # Add to the pending set so the poller knows which sessions to check
        await r.sadd(_PENDING_SET_KEY, session_id)

        logger.info(
            "Started empty_timeout for session '%s' (%ds)",
            session_id,
            EMPTY_TIMEOUT_SECONDS,
        )

    async def cancel_timeout(self, session_id: str) -> None:
        """Cancel the empty_timeout countdown for a session.

        Called when an interviewer rejoins a session that has a pending timeout.
        Deletes the Redis key and removes the session from the pending set.

        Args:
            session_id: The session where an interviewer rejoined.
        """
        r = await self._get_redis()
        key = _timeout_key(session_id)

        # Delete the timeout key (cancels the countdown)
        await r.delete(key)

        # Remove from the pending set
        await r.srem(_PENDING_SET_KEY, session_id)

        logger.info("Cancelled empty_timeout for session '%s'", session_id)

    async def has_pending_timeout(self, session_id: str) -> bool:
        """Check if a session has a pending timeout countdown.

        Args:
            session_id: The session to check.

        Returns:
            True if the session has an active timeout countdown.
        """
        r = await self._get_redis()
        key = _timeout_key(session_id)
        return await r.exists(key) == 1

    async def start_worker(self) -> None:
        """Start the background polling worker.

        The worker periodically checks for expired timeouts and ends
        the corresponding sessions.
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Timeout manager worker started (poll interval: %ds)", _POLL_INTERVAL)

    async def stop_worker(self) -> None:
        """Stop the background polling worker."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Timeout manager worker stopped")

    async def close(self) -> None:
        """Stop the worker and close the Redis connection."""
        await self.stop_worker()
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _poll_loop(self) -> None:
        """Background loop that checks for expired timeouts."""
        while self._running:
            try:
                await self._check_expired_timeouts()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in timeout manager poll loop")

            await asyncio.sleep(_POLL_INTERVAL)

    async def _check_expired_timeouts(self) -> None:
        """Check all pending timeouts and end sessions whose keys have expired."""
        r = await self._get_redis()

        # Get all session IDs with pending timeouts
        pending_session_ids = await r.smembers(_PENDING_SET_KEY)

        if not pending_session_ids:
            return

        for session_id in pending_session_ids:
            key = _timeout_key(session_id)
            # If the key no longer exists, the TTL has expired
            exists = await r.exists(key)
            if not exists:
                # Timeout expired — auto-end the session
                logger.info(
                    "Timeout expired for session '%s', auto-ending session",
                    session_id,
                )
                await self._auto_end_session(session_id)
                # Remove from pending set
                await r.srem(_PENDING_SET_KEY, session_id)

    async def _auto_end_session(self, session_id: str) -> None:
        """End a session due to timeout expiration.

        Transitions the session to "ended", disconnects all participants,
        and deletes the LiveKit room.

        Args:
            session_id: The session to end.
        """
        session_factory = get_async_session_factory()

        async with session_factory() as db:
            try:
                # Fetch the session
                result = await db.execute(
                    select(InterviewSession).where(InterviewSession.id == session_id)
                )
                session = result.scalar_one_or_none()

                if session is None:
                    logger.warning(
                        "Session '%s' not found during auto-end", session_id
                    )
                    return

                # Only end sessions that are still active
                if session.status != "active":
                    logger.info(
                        "Session '%s' is already '%s', skipping auto-end",
                        session_id,
                        session.status,
                    )
                    return

                # Transition to ended
                session.status = "ended"
                session.ended_at = datetime.now(UTC)

                # Disconnect all connected participants
                participants_result = await db.execute(
                    select(SessionParticipant).where(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.status == "connected",
                    )
                )
                connected_participants = participants_result.scalars().all()

                now = datetime.now(UTC)
                for participant in connected_participants:
                    participant.status = "disconnected"
                    participant.left_at = now

                await db.commit()

                logger.info(
                    "Auto-ended session '%s' (disconnected %d participants)",
                    session_id,
                    len(connected_participants),
                )

                # Delete the LiveKit room
                try:
                    livekit = LiveKitAdapter()
                    await livekit.delete_room(session.room_name)
                    logger.info(
                        "Deleted LiveKit room '%s' for auto-ended session '%s'",
                        session.room_name,
                        session_id,
                    )
                except Exception:
                    logger.exception(
                        "Failed to delete LiveKit room '%s' for session '%s'",
                        session.room_name,
                        session_id,
                    )

            except Exception:
                logger.exception(
                    "Failed to auto-end session '%s'", session_id
                )
                await db.rollback()


# Module-level singleton for use across the application
_timeout_manager: TimeoutManager | None = None


def get_timeout_manager() -> TimeoutManager:
    """Get or create the module-level TimeoutManager singleton."""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager
