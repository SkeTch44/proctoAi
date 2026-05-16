"""
CheatMonitor — Orchestrates real-time cheat detection for interview sessions.

Manages the monitoring lifecycle (start/stop/pause/resume), coordinates with
proctoring-svc for detection, aggregates risk scores, and dispatches alerts
to interviewers via LiveKit data channels.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import UTC, datetime

import httpx
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import InvalidSessionStateError, SessionNotFoundError
from app.models.cheat_alert import CheatAlert
from app.models.cheat_monitoring_state import CheatMonitoringState
from app.models.interview_session import InterviewSession
from app.schemas.cheat_detection import (
    CheatAlertResponse,
    CheatDetectionResult,
    RiskSummary,
)
from app.services.alert_dispatcher import AlertDispatcher
from app.services.livekit_adapter import LiveKitAdapter
from app.services.risk_engine import aggregate_risk_score, determine_verdict

logger = logging.getLogger(__name__)

# Valid monitoring state transitions.
# Maps current_status -> set of allowed target statuses.
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "inactive": {"active"},
    "active": {"paused", "inactive"},
    "paused": {"active", "inactive"},
}

# Interview-specific base scores for browser events.
# These are used as fallback when proctoring-svc is unavailable.
_BROWSER_EVENT_BASE_SCORES: dict[str, float] = {
    "DEVTOOLS_OPEN": 80.0,
    "TAB_SWITCH": 40.0,
    "COPY_DETECTED": 30.0,
    "PASTE_DETECTED": 30.0,
    "FULLSCREEN_EXIT": 60.0,
}


class MonitoringAlreadyActiveError(Exception):
    """Raised when monitoring start is attempted on a session that already has active monitoring."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"Monitoring is already active for session '{session_id}'."
        )


class MonitoringNotActiveError(Exception):
    """Raised when an operation requires active monitoring but none exists."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"No active monitoring found for session '{session_id}'."
        )


class InvalidMonitoringStateError(Exception):
    """Raised when an invalid monitoring state transition is attempted."""

    def __init__(self, session_id: str, current_status: str, target_status: str):
        self.session_id = session_id
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition monitoring for session '{session_id}' "
            f"from '{current_status}' to '{target_status}'."
        )


class CheatMonitor:
    """Orchestrates real-time cheat detection for interview sessions.

    Manages the lifecycle of monitoring per session, coordinates with
    proctoring-svc, aggregates results, and dispatches alerts via LiveKit
    data channels.
    """

    def __init__(
        self,
        db: AsyncSession,
        livekit: LiveKitAdapter,
        redis_client: Redis,
        http_client: httpx.AsyncClient,
    ):
        self.db = db
        self.livekit = livekit
        self.redis_client = redis_client
        self.http_client = http_client

        # Active monitoring tasks keyed by session_id
        self._monitoring_tasks: dict[str, asyncio.Task] = {}

    async def start_monitoring(
        self,
        session_id: str,
        room_name: str,
        candidate_identity: str,
    ) -> None:
        """Start cheat monitoring for an interview session.

        Validates the session is active and no monitoring is already running,
        creates a CheatMonitoringState record, initializes Redis keys for
        signal tracking, starts the background monitoring loop, and notifies
        interviewers via LiveKit data channel.

        Args:
            session_id: The interview session to monitor.
            room_name: The LiveKit room name for the session.
            candidate_identity: The LiveKit identity of the candidate.

        Raises:
            SessionNotFoundError: If the session does not exist.
            InvalidSessionStateError: If the session is not active.
            MonitoringAlreadyActiveError: If monitoring is already active for this session.
            InvalidMonitoringStateError: If the state transition is not allowed.
        """
        # Validate session exists and is active
        session = await self._get_session(session_id)
        if session.status != "active":
            raise InvalidSessionStateError(session.status, "active")

        # Check for existing monitoring state
        state = await self._get_monitoring_state(session_id)

        if state is not None:
            if state.status == "active":
                raise MonitoringAlreadyActiveError(session_id)
            if state.status not in _VALID_TRANSITIONS or "active" not in _VALID_TRANSITIONS.get(state.status, set()):
                raise InvalidMonitoringStateError(session_id, state.status, "active")
            # Transition from inactive/paused to active
            state.status = "active"
            state.started_at = datetime.now(UTC)
            state.stopped_at = None
        else:
            # Create new monitoring state record
            state = CheatMonitoringState(
                session_id=session_id,
                status="active",
                started_at=datetime.now(UTC),
            )
            self.db.add(state)

        await self.db.commit()

        # Initialize Redis keys for signal tracking
        await self._initialize_redis_keys(session_id)

        # Start the background monitoring loop
        task = asyncio.create_task(
            self._monitoring_loop(session_id, room_name, candidate_identity)
        )
        self._monitoring_tasks[session_id] = task

        # Notify interviewers via LiveKit data channel
        await self._notify_interviewers(
            room_name,
            {"type": "monitoring_started", "session_id": session_id},
        )

        logger.info(
            "Cheat monitoring started for session '%s' in room '%s'",
            session_id,
            room_name,
        )

    async def stop_monitoring(self, session_id: str) -> None:
        """Stop cheat monitoring for an interview session.

        Sets monitoring state to inactive, records stopped_at timestamp,
        cancels the background monitoring task, cleans up Redis keys,
        and notifies interviewers.

        Args:
            session_id: The session to stop monitoring for.

        Raises:
            MonitoringNotActiveError: If no monitoring state exists for the session.
            InvalidMonitoringStateError: If the current state cannot transition to inactive.
        """
        state = await self._get_monitoring_state(session_id)
        if state is None:
            raise MonitoringNotActiveError(session_id)

        current_status = state.status
        if "inactive" not in _VALID_TRANSITIONS.get(current_status, set()):
            raise InvalidMonitoringStateError(session_id, current_status, "inactive")

        # Update state to inactive with final timestamp
        state.status = "inactive"
        state.stopped_at = datetime.now(UTC)
        await self.db.commit()

        # Cancel the background monitoring task
        task = self._monitoring_tasks.pop(session_id, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Clean up Redis keys
        await self._cleanup_redis_keys(session_id)

        # Get room_name for notification
        session = await self._get_session(session_id)

        # Notify interviewers
        await self._notify_interviewers(
            session.room_name,
            {"type": "monitoring_stopped", "session_id": session_id},
        )

        logger.info("Cheat monitoring stopped for session '%s'", session_id)

    async def pause_monitoring(self, session_id: str) -> None:
        """Pause cheat monitoring without destroying state.

        The monitoring loop will stop processing frames/events but the
        monitoring state and Redis data are preserved for resumption.

        Args:
            session_id: The session to pause monitoring for.

        Raises:
            MonitoringNotActiveError: If no monitoring state exists.
            InvalidMonitoringStateError: If the current state cannot transition to paused.
        """
        state = await self._get_monitoring_state(session_id)
        if state is None:
            raise MonitoringNotActiveError(session_id)

        current_status = state.status
        if "paused" not in _VALID_TRANSITIONS.get(current_status, set()):
            raise InvalidMonitoringStateError(session_id, current_status, "paused")

        state.status = "paused"
        await self.db.commit()

        # Get room_name for notification
        session = await self._get_session(session_id)

        # Notify interviewers
        await self._notify_interviewers(
            session.room_name,
            {"type": "monitoring_paused", "session_id": session_id},
        )

        logger.info("Cheat monitoring paused for session '%s'", session_id)

    async def resume_monitoring(self, session_id: str) -> None:
        """Resume paused cheat monitoring.

        Transitions monitoring state from paused back to active. The
        monitoring loop (still running) will resume processing.

        Args:
            session_id: The session to resume monitoring for.

        Raises:
            MonitoringNotActiveError: If no monitoring state exists.
            InvalidMonitoringStateError: If the current state cannot transition to active.
        """
        state = await self._get_monitoring_state(session_id)
        if state is None:
            raise MonitoringNotActiveError(session_id)

        current_status = state.status
        if "active" not in _VALID_TRANSITIONS.get(current_status, set()):
            raise InvalidMonitoringStateError(session_id, current_status, "active")

        state.status = "active"
        await self.db.commit()

        # Get room_name for notification
        session = await self._get_session(session_id)

        # Notify interviewers
        await self._notify_interviewers(
            session.room_name,
            {"type": "monitoring_resumed", "session_id": session_id},
        )

        logger.info("Cheat monitoring resumed for session '%s'", session_id)

    async def is_monitoring_active(self, session_id: str) -> bool:
        """Check if monitoring is currently active for a session.

        Args:
            session_id: The session to check.

        Returns:
            True if monitoring state is "active", False otherwise.
        """
        state = await self._get_monitoring_state(session_id)
        if state is None:
            return False
        return state.status == "active"

    async def get_session_risk_summary(self, session_id: str) -> RiskSummary:
        """Get an aggregated risk summary for a session.

        Fetches the monitoring state, aggregates alert counts by severity and
        type from the database, retrieves the current risk score from Redis
        (falling back to the monitoring state), calculates monitoring duration,
        and returns the top 3 active signals.

        Args:
            session_id: The interview session identifier.

        Returns:
            A RiskSummary model with current risk assessment data.
        """
        # Fetch monitoring state
        state = await self._get_monitoring_state(session_id)

        # Default values when no monitoring state exists
        if state is None:
            return RiskSummary(
                session_id=session_id,
                current_score=0.0,
                current_verdict="SAFE",
                total_alerts=0,
                alerts_by_severity={},
                alerts_by_type={},
                monitoring_duration_seconds=0.0,
                frames_processed=0,
                events_processed=0,
                top_signals=[],
            )

        # Get current risk score from Redis (fallback to monitoring state)
        current_score = state.current_risk_score or 0.0
        try:
            redis_score = await self.redis_client.get(f"cheat:risk:{session_id}")
            if redis_score is not None:
                raw = redis_score.decode() if isinstance(redis_score, bytes) else redis_score
                current_score = float(raw)
        except Exception:
            logger.warning(
                "Failed to fetch risk score from Redis for session '%s'; using DB value",
                session_id,
            )

        current_verdict = state.current_verdict or "SAFE"

        # Aggregate alert counts by severity
        severity_query = (
            select(CheatAlert.severity, func.count(CheatAlert.id))
            .where(CheatAlert.session_id == session_id)
            .group_by(CheatAlert.severity)
        )
        severity_result = await self.db.execute(severity_query)
        alerts_by_severity: dict[str, int] = {
            row[0]: row[1] for row in severity_result.all()
        }

        # Aggregate alert counts by type
        type_query = (
            select(CheatAlert.alert_type, func.count(CheatAlert.id))
            .where(CheatAlert.session_id == session_id)
            .group_by(CheatAlert.alert_type)
        )
        type_result = await self.db.execute(type_query)
        alerts_by_type: dict[str, int] = {
            row[0]: row[1] for row in type_result.all()
        }

        # Total alerts
        total_alerts = sum(alerts_by_severity.values())

        # Calculate monitoring duration
        monitoring_duration_seconds = 0.0
        if state.started_at is not None:
            end_time = state.stopped_at if state.stopped_at else datetime.now(UTC)
            # Ensure started_at is timezone-aware for subtraction
            started = state.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)
            monitoring_duration_seconds = (end_time - started).total_seconds()

        # Get top 3 active signals from Redis signal history
        top_signals: list[dict] = []
        try:
            signals_raw = await self.redis_client.hgetall(f"cheat:signals:{session_id}")
            if signals_raw:
                now = time.time()
                active_signals = []
                for key, value in signals_raw.items():
                    signal_name = key.decode() if isinstance(key, bytes) else key
                    raw_value = value.decode() if isinstance(value, bytes) else value
                    data = json.loads(raw_value)
                    # Only include signals within the 30-second window
                    if now - data.get("last_seen", 0) < 30 and data.get("score", 0) > 0:
                        active_signals.append(
                            {"signal": signal_name, "score": data["score"]}
                        )
                # Sort by score descending and take top 3
                active_signals.sort(key=lambda s: s["score"], reverse=True)
                top_signals = active_signals[:3]
        except Exception:
            logger.warning(
                "Failed to fetch signal history from Redis for session '%s'",
                session_id,
            )

        return RiskSummary(
            session_id=session_id,
            current_score=current_score,
            current_verdict=current_verdict,
            total_alerts=total_alerts,
            alerts_by_severity=alerts_by_severity,
            alerts_by_type=alerts_by_type,
            monitoring_duration_seconds=monitoring_duration_seconds,
            frames_processed=state.total_frames_processed or 0,
            events_processed=state.total_events_processed or 0,
            top_signals=top_signals,
        )

    async def get_alert_history(
        self, session_id: str, limit: int = 50
    ) -> list[CheatAlertResponse]:
        """Get paginated alert history for a session.

        Queries CheatAlert records ordered by creation time descending
        (most recent first), limited to the specified count.

        Args:
            session_id: The interview session identifier.
            limit: Maximum number of alerts to return (default 50, max 100).

        Returns:
            List of CheatAlertResponse models.
        """
        # Enforce maximum limit of 100
        effective_limit = min(limit, 100)

        query = (
            select(CheatAlert)
            .where(CheatAlert.session_id == session_id)
            .order_by(CheatAlert.created_at.desc())
            .limit(effective_limit)
        )
        result = await self.db.execute(query)
        alerts = result.scalars().all()

        return [
            CheatAlertResponse(
                id=alert.id,
                session_id=alert.session_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                score=alert.score,
                confidence=alert.confidence,
                details=alert.details,
                created_at=alert.created_at,
                acknowledged=alert.acknowledged or False,
            )
            for alert in alerts
        ]

    async def process_browser_event(
        self,
        session_id: str,
        event_type: str,
        details: dict,
        timestamp: str,
    ) -> CheatDetectionResult:
        """Process a browser-originated cheat event from the candidate.

        Validates monitoring is active, deduplicates events, forwards to
        proctoring-svc for scoring, aggregates risk, and dispatches alerts
        when thresholds are exceeded.

        Args:
            session_id: The interview session identifier.
            event_type: The type of browser event (e.g., TAB_SWITCH, DEVTOOLS_OPEN).
            details: Signal-specific metadata from the browser.
            timestamp: ISO 8601 timestamp of the event.

        Returns:
            CheatDetectionResult with current assessment.
        """
        # Step 1: Validate monitoring is active
        state = await self._get_monitoring_state(session_id)
        if state is None or state.status != "active":
            return CheatDetectionResult(
                suspicious=False,
                score=0.0,
                confidence=0.0,
                verdict="SAFE",
                alert_type=event_type.upper(),
                signals={},
                should_alert=False,
                details={},
            )

        # Step 2: Deduplication check using composite key hash
        event_hash = self._compute_event_hash(event_type, timestamp)
        dedup_key = f"cheat:events:{session_id}"

        cached_result = await self._check_deduplication(dedup_key, event_hash)
        if cached_result is not None:
            return cached_result

        # Step 3: Forward to proctoring-svc
        event_score = await self._forward_event_to_proctoring(
            session_id, event_type, details, timestamp
        )

        # Step 4: Apply interview-specific scoring adjustments
        adjusted_score = self._apply_interview_scoring(event_type, event_score)

        # Step 5: Update running risk score via aggregate_risk_score
        current_risk = await aggregate_risk_score(
            session_id=session_id,
            new_signal=event_type.upper(),
            new_score=adjusted_score,
            redis_client=self.redis_client,
        )

        # Step 6: Determine verdict
        verdict = determine_verdict(current_risk)

        # Step 7: Set should_alert
        should_alert = verdict in ("HIGH", "CRITICAL")

        result = CheatDetectionResult(
            suspicious=adjusted_score > 0,
            score=adjusted_score,
            confidence=0.9,  # Browser events have high confidence
            verdict=verdict,
            alert_type=event_type.upper(),
            signals={event_type.upper(): adjusted_score},
            should_alert=should_alert,
            details=details,
        )

        # Step 8: If should_alert, create alert and dispatch
        if should_alert:
            alert = await self._create_and_persist_alert(session_id, result)
            session = await self._get_session(session_id)
            dispatcher = AlertDispatcher(self.livekit)
            await dispatcher.dispatch_alert(session_id, session.room_name, alert)

        # Step 9: Increment event count in monitoring state
        state.total_events_processed = (state.total_events_processed or 0) + 1
        state.current_risk_score = current_risk
        state.current_verdict = verdict
        await self.db.commit()

        # Cache result for deduplication (store for 30 seconds)
        await self._store_dedup_result(dedup_key, event_hash, result)

        return result

    # ─── Private helpers ───────────────────────────────────────────────

    async def _get_session(self, session_id: str) -> InterviewSession:
        """Fetch an interview session by ID.

        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    async def _get_monitoring_state(
        self, session_id: str
    ) -> CheatMonitoringState | None:
        """Fetch the monitoring state for a session, or None if not found."""
        result = await self.db.execute(
            select(CheatMonitoringState).where(
                CheatMonitoringState.session_id == session_id
            )
        )
        return result.scalar_one_or_none()

    async def _initialize_redis_keys(self, session_id: str) -> None:
        """Initialize Redis keys for signal tracking.

        Sets up the signal history hash and risk score key.
        """
        try:
            # Initialize risk score to 0
            await self.redis_client.set(f"cheat:risk:{session_id}", "0.0")
            # Clear any stale signal history
            await self.redis_client.delete(f"cheat:signals:{session_id}")
        except Exception:
            logger.warning(
                "Failed to initialize Redis keys for session '%s'; "
                "will use in-memory fallback",
                session_id,
            )

    async def _cleanup_redis_keys(self, session_id: str) -> None:
        """Remove Redis keys associated with a monitoring session."""
        try:
            await self.redis_client.delete(
                f"cheat:risk:{session_id}",
                f"cheat:signals:{session_id}",
                f"cheat:events:{session_id}",
            )
        except Exception:
            logger.warning(
                "Failed to clean up Redis keys for session '%s'",
                session_id,
            )

    def _compute_event_hash(self, event_type: str, timestamp: str) -> str:
        """Compute a hash for deduplication from event_type + timestamp."""
        raw = f"{event_type}:{timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _check_deduplication(
        self, dedup_key: str, event_hash: str
    ) -> CheatDetectionResult | None:
        """Check if an event has already been processed.

        Returns the cached CheatDetectionResult if duplicate, None otherwise.
        """
        try:
            # Check if hash exists in the Redis set
            is_member = await self.redis_client.sismember(dedup_key, event_hash)
            if is_member:
                # Retrieve cached result
                cached_raw = await self.redis_client.get(
                    f"{dedup_key}:{event_hash}"
                )
                if cached_raw:
                    cached_data = json.loads(
                        cached_raw.decode()
                        if isinstance(cached_raw, bytes)
                        else cached_raw
                    )
                    return CheatDetectionResult(**cached_data)
            return None
        except Exception:
            logger.warning("Redis deduplication check failed; proceeding without dedup")
            return None

    async def _store_dedup_result(
        self, dedup_key: str, event_hash: str, result: CheatDetectionResult
    ) -> None:
        """Store event hash and result for deduplication (TTL 30 seconds)."""
        try:
            # Add hash to the set
            await self.redis_client.sadd(dedup_key, event_hash)
            # Store the result with a 30-second TTL
            result_key = f"{dedup_key}:{event_hash}"
            await self.redis_client.set(
                result_key,
                result.model_dump_json(),
                ex=30,
            )
            # Set TTL on the set member tracking (expire individual hash after 30s)
            # We use a separate key for the result; the set itself persists for the session
        except Exception:
            logger.warning("Failed to store dedup result in Redis")

    async def _forward_event_to_proctoring(
        self,
        session_id: str,
        event_type: str,
        details: dict,
        timestamp: str,
    ) -> float:
        """Forward a browser event to proctoring-svc and return the score.

        Falls back to local scoring if proctoring-svc is unavailable.
        """
        settings = get_settings()
        proctoring_url = f"{settings.PROCTORING_SVC_URL}/api/v1/proctoring/event"

        payload = {
            "session_id": session_id,
            "session_kind": "interview",
            "event_type": event_type.lower(),
            "details": json.dumps(details) if isinstance(details, dict) else str(details),
            "content": details.get("content", "") if isinstance(details, dict) else "",
            "timestamp": timestamp,
        }

        try:
            response = await self.http_client.post(
                proctoring_url,
                json=payload,
                timeout=3.0,
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("score", 0.0))
            else:
                logger.warning(
                    "proctoring-svc returned %d for event; using local scoring",
                    response.status_code,
                )
                return self._get_local_event_score(event_type)
        except (httpx.TimeoutException, httpx.ConnectError, Exception) as exc:
            logger.warning(
                "proctoring-svc unavailable for event processing: %s; using local scoring",
                exc,
            )
            return self._get_local_event_score(event_type)

    def _apply_interview_scoring(self, event_type: str, base_score: float) -> float:
        """Apply interview-specific scoring adjustments to a browser event score.

        Uses predefined base scores for known event types when the proctoring-svc
        returns 0 or as a minimum floor.
        """
        event_key = event_type.upper()
        interview_base = _BROWSER_EVENT_BASE_SCORES.get(event_key, base_score)

        # Use the higher of proctoring-svc score and interview base score
        adjusted = max(base_score, interview_base)
        return min(100.0, max(0.0, adjusted))

    def _get_local_event_score(self, event_type: str) -> float:
        """Get a local fallback score for a browser event type."""
        return _BROWSER_EVENT_BASE_SCORES.get(event_type.upper(), 20.0)

    async def _create_and_persist_alert(
        self, session_id: str, result: CheatDetectionResult
    ) -> CheatAlert:
        """Create a CheatAlert record and persist it to the database."""
        alert = CheatAlert(
            session_id=session_id,
            alert_type=result.alert_type,
            severity=result.verdict,
            score=result.score,
            confidence=result.confidence,
            details=result.details,
            created_at=datetime.now(UTC),
        )
        self.db.add(alert)

        # Increment alert count in monitoring state
        state = await self._get_monitoring_state(session_id)
        if state:
            state.total_alerts_generated = (state.total_alerts_generated or 0) + 1

        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def _notify_interviewers(self, room_name: str, payload: dict) -> None:
        """Send a notification to interviewers via LiveKit data channel.

        Failures are logged but do not raise — alert delivery is best-effort.
        """
        try:
            await self.livekit.send_data(
                room_name=room_name,
                data=json.dumps(payload),
            )
        except Exception:
            logger.warning(
                "Failed to notify interviewers in room '%s': %s",
                room_name,
                payload.get("type", "unknown"),
            )

    async def _monitoring_loop(
        self,
        session_id: str,
        room_name: str,
        candidate_identity: str,
    ) -> None:
        """Background monitoring loop — placeholder for task 4.3.

        This loop will be fully implemented in task 4.3. For now it simply
        waits while monitoring is active, checking the state periodically.
        """
        try:
            while True:
                # Check if monitoring is still active or paused
                state = await self._get_monitoring_state(session_id)
                if state is None or state.status == "inactive":
                    break

                # If paused, just sleep and re-check
                if state.status == "paused":
                    await asyncio.sleep(1.0)
                    continue

                # Active monitoring — full implementation in task 4.3
                await asyncio.sleep(2.0)

        except asyncio.CancelledError:
            logger.info(
                "Monitoring loop cancelled for session '%s'", session_id
            )
            raise
