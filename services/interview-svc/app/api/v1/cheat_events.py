"""Cheat detection API endpoints.

Implements:
- POST /api/v1/interviews/sessions/{session_id}/cheat-events — Report a browser cheat event
- GET /api/v1/interviews/sessions/{session_id}/cheat-summary — Get risk summary
- GET /api/v1/interviews/sessions/{session_id}/cheat-alerts — Get alert history
- POST /api/v1/interviews/sessions/{session_id}/cheat-monitoring/start — Start monitoring
- POST /api/v1/interviews/sessions/{session_id}/cheat-monitoring/stop — Stop monitoring
"""

from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenUser, get_current_user, require_role
from app.core.database import get_db
from app.core.exceptions import (
    InvalidSessionStateError,
    SessionNotFoundError,
)
from app.schemas.cheat_detection import (
    CheatAlertResponse,
    CheatDetectionResult,
    CheatEventRequest,
    RiskSummary,
)
from app.services.cheat_monitor import (
    CheatMonitor,
    MonitoringAlreadyActiveError,
    MonitoringNotActiveError,
    InvalidMonitoringStateError,
)
from app.services.livekit_adapter import LiveKitAdapter

router = APIRouter(
    prefix="/api/v1/interviews/sessions",
    tags=["cheat-detection"],
)


# ─── Dependency helpers ────────────────────────────────────────────────


async def _get_redis() -> Redis:
    """Provide a Redis client instance.

    In production this would be managed via app state or a connection pool.
    For now, create a connection from settings.
    """
    from app.core.config import get_settings

    settings = get_settings()
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


async def _get_http_client() -> httpx.AsyncClient:
    """Provide an httpx AsyncClient for outbound calls to proctoring-svc."""
    async with httpx.AsyncClient(timeout=3.0) as client:
        yield client


def _build_cheat_monitor(
    db: AsyncSession,
    redis_client: Redis,
    http_client: httpx.AsyncClient,
) -> CheatMonitor:
    """Build a CheatMonitor with all required dependencies."""
    livekit = LiveKitAdapter()
    return CheatMonitor(
        db=db,
        livekit=livekit,
        redis_client=redis_client,
        http_client=http_client,
    )


# ─── Endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/{session_id}/cheat-events",
    response_model=CheatDetectionResult,
    summary="Report a browser cheat event",
)
async def report_cheat_event(
    session_id: str,
    body: CheatEventRequest,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(_get_redis),
    http_client: httpx.AsyncClient = Depends(_get_http_client),
):
    """Report a browser-originated cheat event from the candidate.

    Any authenticated user (candidate) can report events for their session.
    The event is forwarded to CheatMonitor for processing and risk scoring.
    """
    monitor = _build_cheat_monitor(db, redis_client, http_client)

    try:
        result = await monitor.process_browser_event(
            session_id=session_id,
            event_type=body.event_type,
            details=body.details,
            timestamp=body.timestamp,
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    return result


@router.get(
    "/{session_id}/cheat-summary",
    response_model=RiskSummary,
    summary="Get risk summary for a session",
)
async def get_cheat_summary(
    session_id: str,
    user: TokenUser = Depends(require_role("interviewer", "admin")),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(_get_redis),
    http_client: httpx.AsyncClient = Depends(_get_http_client),
):
    """Get the aggregated risk summary for a session.

    Requires interviewer or admin role.
    Returns current risk score, verdict, alert counts, and top signals.
    """
    monitor = _build_cheat_monitor(db, redis_client, http_client)

    try:
        summary = await monitor.get_session_risk_summary(session_id=session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    return summary


@router.get(
    "/{session_id}/cheat-alerts",
    response_model=List[CheatAlertResponse],
    summary="Get alert history for a session",
)
async def get_cheat_alerts(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    user: TokenUser = Depends(require_role("interviewer", "admin")),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(_get_redis),
    http_client: httpx.AsyncClient = Depends(_get_http_client),
):
    """Get paginated alert history for a session.

    Requires interviewer or admin role.
    Returns alerts ordered by creation time descending (most recent first).
    """
    monitor = _build_cheat_monitor(db, redis_client, http_client)

    try:
        alerts = await monitor.get_alert_history(
            session_id=session_id,
            limit=limit,
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    return alerts


@router.post(
    "/{session_id}/cheat-monitoring/start",
    response_model=dict,
    summary="Start cheat monitoring for a session",
)
async def start_cheat_monitoring(
    session_id: str,
    user: TokenUser = Depends(require_role("interviewer", "admin")),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(_get_redis),
    http_client: httpx.AsyncClient = Depends(_get_http_client),
):
    """Start cheat monitoring for an interview session.

    Requires interviewer or admin role.
    The session must be active and not already being monitored.
    """
    monitor = _build_cheat_monitor(db, redis_client, http_client)

    # Retrieve session to get room_name and candidate identity
    session = await monitor._get_session(session_id)

    # Determine candidate identity (use session_id as placeholder;
    # in production this would be resolved from participants)
    candidate_identity = f"candidate-{session_id}"

    try:
        await monitor.start_monitoring(
            session_id=session_id,
            room_name=session.room_name,
            candidate_identity=candidate_identity,
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    except InvalidSessionStateError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session '{session_id}' is not active",
        )
    except MonitoringAlreadyActiveError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Monitoring is already active for session '{session_id}'",
        )
    except InvalidMonitoringStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return {
        "session_id": session_id,
        "status": "active",
        "message": "Cheat monitoring started",
    }


@router.post(
    "/{session_id}/cheat-monitoring/stop",
    response_model=dict,
    summary="Stop cheat monitoring for a session",
)
async def stop_cheat_monitoring(
    session_id: str,
    user: TokenUser = Depends(require_role("interviewer", "admin")),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(_get_redis),
    http_client: httpx.AsyncClient = Depends(_get_http_client),
):
    """Stop cheat monitoring for an interview session.

    Requires interviewer or admin role.
    Monitoring must be active or paused to be stopped.
    """
    monitor = _build_cheat_monitor(db, redis_client, http_client)

    try:
        await monitor.stop_monitoring(session_id=session_id)
    except MonitoringNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No active monitoring found for session '{session_id}'",
        )
    except InvalidMonitoringStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return {
        "session_id": session_id,
        "status": "inactive",
        "message": "Cheat monitoring stopped",
    }
