"""LiveKit webhook handler — processes participant and room lifecycle events.

Handles:
- participant_disconnected: Updates participant status, triggers empty_timeout if last interviewer left
- room_finished: Cleans up session state (transitions to "ended" if still active)

Validates webhook signatures using the LiveKit API secret via TokenVerifier/WebhookReceiver.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Header, Request, Response
from livekit import api
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import get_async_session_factory
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.livekit_adapter import LiveKitAdapter
from app.services.timeout_manager import get_timeout_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interviews/webhooks", tags=["webhooks"])


def _get_webhook_receiver() -> api.WebhookReceiver:
    """Create a WebhookReceiver using the configured LiveKit API key and secret."""
    settings = get_settings()
    token_verifier = api.TokenVerifier(
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    return api.WebhookReceiver(token_verifier)


def _extract_session_id_from_room_name(room_name: str) -> str | None:
    """Extract session ID prefix from a LiveKit room name.

    Room names follow the pattern 'interview_{session_id[:8]}'.
    Returns the 8-char prefix used to look up the session.
    """
    if room_name and room_name.startswith("interview_"):
        return room_name[len("interview_"):]
    return None


@router.post("/livekit")
async def livekit_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Response:
    """Receive and process LiveKit webhook events.

    Validates the webhook signature using the LiveKit API secret, then
    dispatches to the appropriate handler based on event type.

    LiveKit sends the JWT token in the Authorization header and the
    event payload as the raw request body.
    """
    # Read raw body for signature verification
    body = await request.body()
    body_str = body.decode("utf-8")

    # Validate webhook signature
    if not authorization:
        logger.warning("LiveKit webhook received without Authorization header")
        return Response(status_code=401, content="Missing authorization")

    try:
        receiver = _get_webhook_receiver()
        event = receiver.receive(body_str, authorization)
    except Exception as exc:
        logger.warning("LiveKit webhook signature validation failed: %s", exc)
        return Response(status_code=401, content="Invalid webhook signature")

    # Dispatch based on event type
    event_type = event.event
    logger.info("Received LiveKit webhook event: %s", event_type)

    try:
        if event_type == "participant_disconnected":
            await _handle_participant_disconnected(event)
        elif event_type == "room_finished":
            await _handle_room_finished(event)
        else:
            logger.debug("Ignoring unhandled LiveKit webhook event: %s", event_type)
    except Exception:
        logger.exception("Error processing LiveKit webhook event '%s'", event_type)
        # Return 200 to avoid LiveKit retrying — we log the error internally
        return Response(status_code=200)

    return Response(status_code=200)


async def _handle_participant_disconnected(event) -> None:
    """Handle participant_disconnected webhook event.

    Updates the participant's status to "disconnected" and checks if they
    were the last interviewer. If so, triggers the empty_timeout countdown.

    Args:
        event: The parsed WebhookEvent from LiveKit.
    """
    room = event.room
    participant = event.participant

    if not room or not participant:
        logger.warning("participant_disconnected event missing room or participant data")
        return

    room_name = room.name
    identity = participant.identity  # This is str(user_id)

    if not room_name or not identity:
        logger.warning(
            "participant_disconnected event has empty room_name or identity"
        )
        return

    logger.info(
        "Participant '%s' disconnected from room '%s'",
        identity,
        room_name,
    )

    session_factory = get_async_session_factory()

    async with session_factory() as db:
        # Find the session by room_name
        session_result = await db.execute(
            select(InterviewSession).where(InterviewSession.room_name == room_name)
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            logger.warning(
                "No session found for room '%s' during participant_disconnected",
                room_name,
            )
            return

        # Session must be active to process disconnections
        if session.status != "active":
            logger.info(
                "Session '%s' is '%s', skipping participant disconnect handling",
                session.id,
                session.status,
            )
            return

        # Find the participant record by user_id (identity) and session_id
        try:
            user_id = int(identity)
        except (ValueError, TypeError):
            logger.warning(
                "Could not parse participant identity '%s' as user_id", identity
            )
            return

        participant_result = await db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session.id,
                SessionParticipant.user_id == user_id,
            )
        )
        db_participant = participant_result.scalar_one_or_none()

        if db_participant is None:
            logger.warning(
                "No participant record found for user_id %d in session '%s'",
                user_id,
                session.id,
            )
            return

        # Only update if currently connected
        if db_participant.status != "connected":
            logger.info(
                "Participant user_id=%d in session '%s' already has status '%s'",
                user_id,
                session.id,
                db_participant.status,
            )
            return

        # Update participant status to "disconnected"
        db_participant.status = "disconnected"
        db_participant.left_at = datetime.now(UTC)

        await db.commit()

        logger.info(
            "Updated participant user_id=%d to 'disconnected' in session '%s'",
            user_id,
            session.id,
        )

        # Check if the disconnected participant was an interviewer
        if db_participant.role == "interviewer":
            # Count remaining connected interviewers
            remaining_result = await db.execute(
                select(func.count(SessionParticipant.id)).where(
                    SessionParticipant.session_id == session.id,
                    SessionParticipant.role == "interviewer",
                    SessionParticipant.status == "connected",
                )
            )
            remaining_interviewers = remaining_result.scalar() or 0

            if remaining_interviewers == 0:
                # Last interviewer left — start the empty_timeout countdown
                logger.info(
                    "Last interviewer left session '%s', starting empty_timeout",
                    session.id,
                )
                timeout_manager = get_timeout_manager()
                await timeout_manager.start_timeout(session.id)


async def _handle_room_finished(event) -> None:
    """Handle room_finished webhook event.

    When LiveKit reports a room has finished (all participants left or
    empty_timeout expired on the LiveKit side), clean up the session state
    by transitioning it to "ended" if still active.

    Args:
        event: The parsed WebhookEvent from LiveKit.
    """
    room = event.room

    if not room:
        logger.warning("room_finished event missing room data")
        return

    room_name = room.name

    if not room_name:
        logger.warning("room_finished event has empty room_name")
        return

    logger.info("Room '%s' finished", room_name)

    session_factory = get_async_session_factory()

    async with session_factory() as db:
        # Find the session by room_name
        session_result = await db.execute(
            select(InterviewSession).where(InterviewSession.room_name == room_name)
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            logger.warning(
                "No session found for room '%s' during room_finished", room_name
            )
            return

        # Only transition if session is still active (or scheduled)
        if session.status == "ended":
            logger.info(
                "Session '%s' already ended, skipping room_finished cleanup",
                session.id,
            )
            return

        # Transition session to "ended"
        session.status = "ended"
        session.ended_at = datetime.now(UTC)

        # Disconnect all connected participants
        participants_result = await db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session.id,
                SessionParticipant.status == "connected",
            )
        )
        connected_participants = list(participants_result.scalars().all())

        now = datetime.now(UTC)
        for p in connected_participants:
            p.status = "disconnected"
            p.left_at = now

        await db.commit()

        logger.info(
            "Room finished: ended session '%s' (disconnected %d participants)",
            session.id,
            len(connected_participants),
        )

        # Cancel any pending timeout for this session
        timeout_manager = get_timeout_manager()
        await timeout_manager.cancel_timeout(session.id)
