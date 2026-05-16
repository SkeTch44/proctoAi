"""AlertDispatcher - Formats and delivers cheat detection alerts via LiveKit data channels.

Responsible for sending real-time alert payloads, periodic risk score updates,
and monitoring status notifications to interviewers connected to a session room.
All delivery is best-effort: failures are logged but never raised to callers.
"""

import json
import logging
from datetime import datetime

from app.services.livekit_adapter import LiveKitAdapter

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """Delivers cheat alerts to interviewers via LiveKit data channels.

    Takes a LiveKitAdapter as a dependency for sending data to rooms.
    All dispatch methods are best-effort: exceptions from the LiveKit layer
    are caught, logged, and swallowed so that callers are never disrupted.
    """

    def __init__(self, livekit_adapter: LiveKitAdapter) -> None:
        self._livekit = livekit_adapter

    async def dispatch_alert(
        self,
        session_id: str,
        room_name: str,
        alert,
    ) -> None:
        """Send a cheat alert to all interviewers in the session room.

        Formats the alert as a JSON payload and sends it via the LiveKit
        data channel. Delivery is best-effort — failures are logged without
        raising.

        Args:
            session_id: The interview session identifier.
            room_name: The LiveKit room to broadcast to.
            alert: A CheatAlert model instance (SQLAlchemy or equivalent).
        """
        try:
            # Format timestamp — handle both datetime objects and strings
            timestamp = alert.created_at
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()

            payload = json.dumps({
                "type": "cheat_alert",
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "score": alert.score,
                "confidence": alert.confidence,
                "details": alert.details,
                "timestamp": timestamp,
                "session_id": session_id,
            })

            await self._livekit.send_data(room_name=room_name, data=payload)
            logger.info(
                "Dispatched cheat_alert to room '%s' (alert_id=%s, type=%s, severity=%s)",
                room_name,
                alert.id,
                alert.alert_type,
                alert.severity,
            )
        except Exception as exc:
            logger.error(
                "Failed to dispatch cheat_alert to room '%s' for session '%s': %s",
                room_name,
                session_id,
                exc,
            )

    async def dispatch_risk_update(
        self,
        session_id: str,
        room_name: str,
        risk_summary,
    ) -> None:
        """Send a periodic risk score update to interviewers.

        Called every 10 seconds during active monitoring to keep interviewers
        informed of the current risk posture.

        Args:
            session_id: The interview session identifier.
            room_name: The LiveKit room to broadcast to.
            risk_summary: A RiskSummary Pydantic model instance.
        """
        try:
            payload = json.dumps({
                "type": "risk_update",
                "session_id": session_id,
                "current_score": risk_summary.current_score,
                "current_verdict": risk_summary.current_verdict,
                "total_alerts": risk_summary.total_alerts,
                "top_signals": risk_summary.top_signals,
            })

            await self._livekit.send_data(room_name=room_name, data=payload)
            logger.debug(
                "Dispatched risk_update to room '%s' (score=%.1f, verdict=%s)",
                room_name,
                risk_summary.current_score,
                risk_summary.current_verdict,
            )
        except Exception as exc:
            logger.error(
                "Failed to dispatch risk_update to room '%s' for session '%s': %s",
                room_name,
                session_id,
                exc,
            )

    async def dispatch_monitoring_status(
        self,
        session_id: str,
        room_name: str,
        status: str,
    ) -> None:
        """Send a monitoring status change notification to interviewers.

        Used to inform interviewers when monitoring starts, stops, pauses,
        or enters/exits a degraded state.

        Args:
            session_id: The interview session identifier.
            room_name: The LiveKit room to broadcast to.
            status: One of "started", "stopped", "paused", "degraded".
        """
        try:
            payload = json.dumps({
                "type": "monitoring_status",
                "session_id": session_id,
                "status": status,
            })

            await self._livekit.send_data(room_name=room_name, data=payload)
            logger.info(
                "Dispatched monitoring_status '%s' to room '%s' for session '%s'",
                status,
                room_name,
                session_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to dispatch monitoring_status '%s' to room '%s' for session '%s': %s",
                status,
                room_name,
                session_id,
                exc,
            )
