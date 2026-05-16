"""Interview session service — core business logic for session lifecycle."""

import json
from datetime import UTC, datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateIntervieweeError,
    DuplicateParticipantError,
    InvalidSessionStateError,
    ParticipantRemovedError,
    PermissionDeniedError,
    SessionEndedError,
    SessionFullError,
    SessionNotFoundError,
)
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.services.livekit_adapter import LiveKitAdapter
from app.services.timeout_manager import get_timeout_manager


class SessionValidationError(Exception):
    """Raised when session creation parameters fail validation."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class LiveKitUnavailableError(Exception):
    """Raised when the LiveKit server is unreachable."""

    def __init__(self, detail: str = "LiveKit server is unavailable"):
        self.detail = detail
        super().__init__(detail)


class CreateSessionResult:
    """Result of a successful session creation."""

    def __init__(self, session_id: str, join_url: str, room_name: str):
        self.session_id = session_id
        self.join_url = join_url
        self.room_name = room_name


class JoinResult:
    """Result of a successful session join."""

    def __init__(
        self,
        livekit_token: str,
        room_name: str,
        session: InterviewSession,
        participants: List[SessionParticipant],
        recording_active: bool = False,
    ):
        self.livekit_token = livekit_token
        self.room_name = room_name
        self.session = session
        self.participants = participants
        self.recording_active = recording_active


class InterviewSessionService:
    """Core service for managing interview session lifecycle."""

    def __init__(self, db: AsyncSession, livekit: LiveKitAdapter):
        self.db = db
        self.livekit = livekit

    async def create_session(
        self,
        creator_id: int,
        title: str,
        scheduled_at: datetime | None = None,
        max_participants: int = 6,
    ) -> CreateSessionResult:
        """
        Create a new interview session.

        Validates inputs, persists the session record, and creates a LiveKit room.
        Rolls back the database transaction if LiveKit room creation fails.

        Args:
            creator_id: ID of the authenticated user creating the session.
            title: Session title (1-500 characters).
            scheduled_at: Optional scheduled start time.
            max_participants: Maximum number of concurrent participants (2-10).

        Returns:
            CreateSessionResult with session_id, join_url, and room_name.

        Raises:
            SessionValidationError: If title or max_participants are invalid.
            LiveKitUnavailableError: If LiveKit room creation fails.
        """
        # Validate title
        if not title or len(title.strip()) == 0:
            raise SessionValidationError(
                "Title must not be empty"
            )
        if len(title) > 500:
            raise SessionValidationError(
                "Title must not exceed 500 characters"
            )

        # Validate max_participants
        if max_participants < 2 or max_participants > 10:
            raise SessionValidationError(
                "max_participants must be between 2 and 10"
            )

        # Generate session ID and room name
        session_id = str(uuid4())
        room_name = f"interview_{session_id[:8]}"

        # Create the session record
        session = InterviewSession(
            id=session_id,
            title=title,
            room_name=room_name,
            creator_id=creator_id,
            status="scheduled",
            max_participants=max_participants,
            scheduled_at=scheduled_at,
        )

        self.db.add(session)
        await self.db.flush()  # Flush to detect DB constraint violations early

        # Create LiveKit room — roll back DB on failure
        try:
            await self.livekit.create_room(
                room_name=room_name,
                max_participants=max_participants,
                empty_timeout=300,
            )
        except Exception as exc:
            await self.db.rollback()
            raise LiveKitUnavailableError(
                f"Failed to create LiveKit room: {exc}"
            ) from exc

        # Commit the session to the database
        await self.db.commit()

        # Build join URL
        join_url = f"/api/v1/interviews/sessions/{session_id}/join"

        return CreateSessionResult(
            session_id=session_id,
            join_url=join_url,
            room_name=room_name,
        )

    async def join_session(
        self,
        session_id: str,
        user_id: int,
        role: str,
        display_name: str,
    ) -> JoinResult:
        """
        Handle a participant joining an interview session.

        Follows the join algorithm from the design document:
        1. Validate session exists and is not ended
        2. Check participant count against max_participants
        3. Enforce single interviewee constraint
        4. Check for rejoin (user previously disconnected)
        5. Reject removed participants
        6. Reject already-connected participants
        7. Create new participant record if not rejoining
        8. Transition session from "scheduled" to "active" on first join
        9. Generate LiveKit token with role-based grants
        10. Return JoinResult with token, room_name, and participant list

        Args:
            session_id: The session to join.
            user_id: The authenticated user's ID.
            role: Participant role ('interviewer', 'interviewee', 'observer').
            display_name: Display name for the participant.

        Returns:
            JoinResult with livekit_token, room_name, session, and participants.

        Raises:
            SessionNotFoundError: If session does not exist.
            SessionEndedError: If session status is "ended".
            SessionFullError: If connected participant count >= max_participants.
            DuplicateIntervieweeError: If a second interviewee tries to join.
            ParticipantRemovedError: If a removed participant tries to rejoin.
            DuplicateParticipantError: If user is already connected.
        """
        # Step 1: Fetch and validate session
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        if session.status == "ended":
            raise SessionEndedError(session_id)

        # Step 2: Check participant limits (count of currently connected participants)
        count_result = await self.db.execute(
            select(func.count(SessionParticipant.id)).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.status == "connected",
            )
        )
        current_count = count_result.scalar() or 0

        if current_count >= session.max_participants:
            raise SessionFullError(session_id, session.max_participants)

        # Step 3: Enforce single interviewee constraint
        if role == "interviewee":
            interviewee_result = await self.db.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.role == "interviewee",
                    SessionParticipant.status == "connected",
                )
            )
            existing_interviewee = interviewee_result.scalar_one_or_none()
            if existing_interviewee is not None:
                raise DuplicateIntervieweeError(session_id)

        # Step 4: Check for existing participant record (rejoin or duplicate)
        existing_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == user_id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            # Step 4a: Rejoin — user previously left (status "disconnected")
            if existing.status == "disconnected":
                existing.status = "connected"
                existing.joined_at = datetime.now(UTC)
                existing.left_at = None
                await self.db.flush()
                participant = existing
            # Step 5: Reject removed participants
            elif existing.status == "removed":
                raise ParticipantRemovedError(session_id, user_id)
            # Step 6: Reject already-connected participants
            elif existing.status == "connected":
                raise DuplicateParticipantError(session_id, user_id)
            else:
                # Unknown status — treat as duplicate
                raise DuplicateParticipantError(session_id, user_id)
        else:
            # Step 7: Create new participant record
            participant = SessionParticipant(
                session_id=session_id,
                user_id=user_id,
                role=role,
                display_name=display_name,
                status="connected",
            )
            self.db.add(participant)
            await self.db.flush()

        # Step 8: Transition session from "scheduled" to "active" on first join
        if session.status == "scheduled":
            session.status = "active"
            session.started_at = datetime.now(UTC)
            await self.db.flush()

        # Commit all changes
        await self.db.commit()

        # Cancel any pending empty_timeout if an interviewer joins/rejoins
        if role == "interviewer":
            timeout_manager = get_timeout_manager()
            await timeout_manager.cancel_timeout(session_id)

        # Step 9: Generate LiveKit token with role-based grants
        token = self.livekit.generate_token(
            room_name=session.room_name,
            identity=str(user_id),
            name=display_name,
            role=role,
        )

        # Step 10: Fetch current participant list
        participants_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id
            )
        )
        participants = list(participants_result.scalars().all())

        return JoinResult(
            livekit_token=token,
            room_name=session.room_name,
            session=session,
            participants=participants,
            recording_active=bool(session.is_recording),
        )

    async def start_recording(
        self,
        session_id: str,
        started_by: int,
    ) -> InterviewSession:
        """
        Start recording for an interview session.

        Sets is_recording=True on the session and broadcasts a
        {"type": "recording_started"} message to all connected participants
        via the LiveKit data channel.

        Args:
            session_id: The session to start recording for.
            started_by: The user ID of the person starting the recording.

        Returns:
            The updated InterviewSession.

        Raises:
            SessionNotFoundError: If session does not exist.
            PermissionDeniedError: If caller is not authorized.
        """
        # Fetch session
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        # Validate permission: caller must be session creator or an interviewer
        if session.creator_id != started_by:
            participant_result = await self.db.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == started_by,
                    SessionParticipant.role == "interviewer",
                )
            )
            caller_participant = participant_result.scalar_one_or_none()
            if caller_participant is None:
                raise PermissionDeniedError(
                    "Only the session creator or an interviewer can start recording."
                )

        # Set recording state
        session.is_recording = True
        await self.db.commit()

        # Broadcast recording_started to all participants
        await self.livekit.send_data(
            room_name=session.room_name,
            data=json.dumps({"type": "recording_started"}),
        )

        return session

    async def stop_recording(
        self,
        session_id: str,
        stopped_by: int,
    ) -> InterviewSession:
        """
        Stop recording for an interview session.

        Sets is_recording=False on the session and broadcasts a
        {"type": "recording_stopped"} message to all connected participants
        via the LiveKit data channel.

        Args:
            session_id: The session to stop recording for.
            stopped_by: The user ID of the person stopping the recording.

        Returns:
            The updated InterviewSession.

        Raises:
            SessionNotFoundError: If session does not exist.
            PermissionDeniedError: If caller is not authorized.
        """
        # Fetch session
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        # Validate permission: caller must be session creator or an interviewer
        if session.creator_id != stopped_by:
            participant_result = await self.db.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == stopped_by,
                    SessionParticipant.role == "interviewer",
                )
            )
            caller_participant = participant_result.scalar_one_or_none()
            if caller_participant is None:
                raise PermissionDeniedError(
                    "Only the session creator or an interviewer can stop recording."
                )

        # Clear recording state
        session.is_recording = False
        await self.db.commit()

        # Broadcast recording_stopped to all participants
        await self.livekit.send_data(
            room_name=session.room_name,
            data=json.dumps({"type": "recording_stopped"}),
        )

        return session

    async def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """
        Retrieve a session by its ID.

        Args:
            session_id: The session ID to look up.

        Returns:
            The InterviewSession if found, or None.
        """
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        user_id: int,
        status: Optional[str] = None,
    ) -> List[InterviewSession]:
        """
        List sessions that a user is involved in (as creator or participant).

        Args:
            user_id: The user whose sessions to list.
            status: Optional status filter ('scheduled', 'active', 'ended').

        Returns:
            List of InterviewSession records.
        """
        # Find sessions where user is the creator OR a participant
        participant_session_ids = (
            select(SessionParticipant.session_id)
            .where(SessionParticipant.user_id == user_id)
            .scalar_subquery()
        )

        query = select(InterviewSession).where(
            (InterviewSession.creator_id == user_id)
            | (InterviewSession.id.in_(participant_session_ids))
        )

        if status is not None:
            query = query.where(InterviewSession.status == status)

        query = query.order_by(InterviewSession.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # Valid status transitions: only forward progression allowed
    _VALID_TRANSITIONS = {
        "scheduled": {"active", "ended"},
        "active": {"ended"},
        "ended": set(),
    }

    async def end_session(
        self,
        session_id: str,
        ended_by: int,
    ) -> InterviewSession:
        """
        End an interview session.

        Validates that the caller is the session creator or an interviewer/admin
        participant, transitions the session status to "ended", disconnects all
        connected participants, and deletes the LiveKit room.

        Args:
            session_id: The session to end.
            ended_by: The user ID of the person ending the session.

        Returns:
            The updated InterviewSession with status "ended".

        Raises:
            SessionNotFoundError: If session does not exist.
            PermissionDeniedError: If caller is not authorized to end the session.
            InvalidSessionStateError: If session cannot transition to "ended"
                (e.g., already ended).
        """
        # Fetch session
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        # Validate permission: caller must be session creator or an interviewer participant
        if session.creator_id != ended_by:
            participant_result = await self.db.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == ended_by,
                    SessionParticipant.role == "interviewer",
                )
            )
            caller_participant = participant_result.scalar_one_or_none()
            if caller_participant is None:
                raise PermissionDeniedError(
                    "Only the session creator or an interviewer can end the session."
                )

        # Enforce status monotonicity
        if "ended" not in self._VALID_TRANSITIONS.get(session.status, set()):
            raise InvalidSessionStateError(session.status, "ended")

        # Transition session to "ended"
        session.status = "ended"
        session.ended_at = datetime.now(UTC)

        # Disconnect all connected participants
        participants_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.status == "connected",
            )
        )
        connected_participants = list(participants_result.scalars().all())

        now = datetime.now(UTC)
        for participant in connected_participants:
            participant.status = "disconnected"
            participant.left_at = now

        await self.db.commit()

        # Delete the LiveKit room (best-effort with retries handled by adapter)
        await self.livekit.delete_room(session.room_name)

        return session

    async def leave_session(
        self,
        session_id: str,
        user_id: int,
    ) -> None:
        """
        Handle a participant voluntarily leaving a session.

        Sets the participant's status to "disconnected" and records the left_at
        timestamp.

        Args:
            session_id: The session the participant is leaving.
            user_id: The user ID of the participant leaving.

        Raises:
            SessionNotFoundError: If session does not exist.
            SessionNotFoundError: If participant is not found in the session.
        """
        # Validate session exists
        session_result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        # Find the participant record
        participant_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == user_id,
            )
        )
        participant = participant_result.scalar_one_or_none()

        if participant is None:
            raise SessionNotFoundError(
                f"Participant with user_id {user_id} not found in session '{session_id}'"
            )

        # Update participant status
        participant.status = "disconnected"
        participant.left_at = datetime.now(UTC)

        await self.db.commit()

    async def list_participants(
        self,
        session_id: str,
    ) -> List[SessionParticipant]:
        """
        List all participants in a session.

        Returns all participant records for the given session including
        user_id, display_name, role, status, and joined_at.

        Args:
            session_id: The session to list participants for.

        Returns:
            List of SessionParticipant records.

        Raises:
            SessionNotFoundError: If session does not exist.
        """
        # Validate session exists
        session_result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        # Fetch all participants for the session
        participants_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id
            )
        )
        return list(participants_result.scalars().all())

    async def remove_participant(
        self,
        session_id: str,
        user_id: int,
        removed_by: int,
    ) -> None:
        """
        Remove a participant from an active session.

        Validates that the caller (removed_by) is an interviewer or admin in the
        session, sets the target participant's status to "removed", records the
        left_at timestamp, and kicks them from the LiveKit room.

        Args:
            session_id: The session to remove the participant from.
            user_id: The user ID of the participant to remove.
            removed_by: The user ID of the caller requesting the removal.

        Raises:
            SessionNotFoundError: If session does not exist.
            PermissionDeniedError: If caller is not an interviewer/admin in the session.
            SessionNotFoundError: If the target participant is not found.
        """
        # Validate session exists
        session_result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        # Validate caller has permission (must be session creator or interviewer)
        if session.creator_id != removed_by:
            caller_result = await self.db.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == removed_by,
                    SessionParticipant.role == "interviewer",
                )
            )
            caller = caller_result.scalar_one_or_none()
            if caller is None:
                raise PermissionDeniedError(
                    "Only an interviewer or admin can remove participants."
                )

        # Find the target participant
        target_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == user_id,
            )
        )
        target = target_result.scalar_one_or_none()

        if target is None:
            raise SessionNotFoundError(
                f"Participant with user_id {user_id} not found in session '{session_id}'"
            )

        # Set participant status to "removed" and record left_at
        target.status = "removed"
        target.left_at = datetime.now(UTC)

        await self.db.commit()

        # Kick participant from the LiveKit room
        await self.livekit.remove_participant(
            room_name=session.room_name,
            identity=str(user_id),
        )
