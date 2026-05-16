"""Participant management API endpoints.

Implements:
- GET /api/v1/interviews/sessions/{session_id}/participants — list participants
- DELETE /api/v1/interviews/sessions/{session_id}/participants/{user_id} — remove participant
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenUser, get_current_user
from app.core.database import get_db
from app.core.exceptions import (
    PermissionDeniedError,
    SessionNotFoundError,
)
from app.schemas.participant import ParticipantResponse
from app.services.livekit_adapter import LiveKitAdapter
from app.services.session_service import InterviewSessionService

router = APIRouter(
    prefix="/api/v1/interviews/sessions",
    tags=["participants"],
)


def _get_session_service(db: AsyncSession) -> InterviewSessionService:
    """Build the InterviewSessionService with its dependencies."""
    livekit = LiveKitAdapter()
    return InterviewSessionService(db=db, livekit=livekit)


@router.get(
    "/{session_id}/participants",
    response_model=List[ParticipantResponse],
    summary="List participants in a session",
)
async def list_participants(
    session_id: str,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all participants in an interview session.

    Only session members (participants or the session creator) can view
    the participant list.
    """
    service = _get_session_service(db)

    # Verify the session exists
    session = await service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Fetch participants to check membership
    try:
        participants = await service.list_participants(session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    # Verify caller is a session member (participant or creator)
    is_creator = session.creator_id == user.user_id
    is_participant = any(p.user_id == user.user_id for p in participants)

    if not is_creator and not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only session members can view the participant list",
        )

    return [ParticipantResponse.model_validate(p) for p in participants]


@router.delete(
    "/{session_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a participant from a session",
)
async def remove_participant(
    session_id: str,
    user_id: int,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a participant from an active interview session.

    Only interviewers or admins can remove participants.
    """
    # Enforce role: only interviewer or admin can remove participants
    if user.role not in ("interviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only interviewers or admins can remove participants",
        )

    service = _get_session_service(db)

    try:
        await service.remove_participant(
            session_id=session_id,
            user_id=user_id,
            removed_by=user.user_id,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
