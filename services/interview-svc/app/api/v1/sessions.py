"""Interview session API endpoints.

Implements:
- POST /api/v1/interviews/sessions — create session (interviewer/admin)
- GET /api/v1/interviews/sessions — list sessions for authenticated user
- GET /api/v1/interviews/sessions/{session_id} — get session details
- POST /api/v1/interviews/sessions/{session_id}/join — join session
- POST /api/v1/interviews/sessions/{session_id}/leave — leave session
- POST /api/v1/interviews/sessions/{session_id}/end — end session (interviewer/admin)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenUser, get_current_user
from app.core.database import get_db
from app.core.exceptions import (
    DuplicateIntervieweeError,
    DuplicateParticipantError,
    InvalidSessionStateError,
    ParticipantRemovedError,
    PermissionDeniedError,
    ServiceUnavailableError,
    SessionEndedError,
    SessionFullError,
    SessionNotFoundError,
)
from app.schemas.participant import ParticipantResponse
from app.schemas.session import (
    CreateSessionRequest,
    JoinSessionRequest,
    JoinSessionResponse,
    SessionResponse,
)
from app.services.livekit_adapter import LiveKitAdapter
from app.services.session_service import (
    InterviewSessionService,
    LiveKitUnavailableError,
    SessionValidationError,
)

router = APIRouter(prefix="/api/v1/interviews/sessions", tags=["sessions"])


def _get_session_service(db: AsyncSession) -> InterviewSessionService:
    """Build the InterviewSessionService with its dependencies."""
    livekit = LiveKitAdapter()
    return InterviewSessionService(db=db, livekit=livekit)


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new interview session",
)
async def create_session(
    body: CreateSessionRequest,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new interview session.

    Requires interviewer or admin role.
    """
    # Enforce role: only interviewer or admin can create sessions
    if user.role not in ("interviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only interviewers or admins can create sessions",
        )

    service = _get_session_service(db)

    try:
        result = await service.create_session(
            creator_id=user.user_id,
            title=body.title,
            scheduled_at=body.scheduled_at,
            max_participants=body.max_participants,
        )
    except SessionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        )
    except LiveKitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.detail,
            headers={"Retry-After": "5"},
        )
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        )

    return {
        "session_id": result.session_id,
        "join_url": result.join_url,
        "room_name": result.room_name,
    }


@router.get(
    "",
    response_model=List[SessionResponse],
    summary="List sessions for authenticated user",
)
async def list_sessions(
    status_filter: Optional[str] = Query(
        None, alias="status", pattern=r"^(scheduled|active|ended)$"
    ),
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List sessions the authenticated user is involved in (as creator or participant)."""
    service = _get_session_service(db)
    sessions = await service.list_sessions(user_id=user.user_id, status=status_filter)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session details",
)
async def get_session(
    session_id: str,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific interview session."""
    service = _get_session_service(db)
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    return SessionResponse.model_validate(session)


@router.post(
    "/{session_id}/join",
    response_model=JoinSessionResponse,
    summary="Join an interview session",
)
async def join_session(
    session_id: str,
    body: JoinSessionRequest,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join an existing interview session.

    Generates a LiveKit token scoped to the session's room with role-based grants.
    """
    service = _get_session_service(db)

    try:
        result = await service.join_session(
            session_id=session_id,
            user_id=user.user_id,
            role=body.role,
            display_name=body.display_name,
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    except SessionEndedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session '{session_id}' has ended",
        )
    except SessionFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is full (max {exc.max_participants} participants)",
        )
    except DuplicateIntervieweeError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session already has an interviewee",
        )
    except ParticipantRemovedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You were removed from this session and cannot rejoin",
        )
    except DuplicateParticipantError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already connected to this session",
        )
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        )

    return JoinSessionResponse(
        livekit_token=result.livekit_token,
        room_name=result.room_name,
        session=SessionResponse.model_validate(result.session),
        participants=[
            ParticipantResponse.model_validate(p) for p in result.participants
        ],
    )


@router.post(
    "/{session_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave an interview session",
)
async def leave_session(
    session_id: str,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Voluntarily leave an interview session."""
    service = _get_session_service(db)

    try:
        await service.leave_session(session_id=session_id, user_id=user.user_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session or participant not found",
        )


@router.post(
    "/{session_id}/end",
    response_model=SessionResponse,
    summary="End an interview session",
)
async def end_session(
    session_id: str,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End an interview session.

    Requires interviewer or admin role. Disconnects all participants and
    deletes the LiveKit room.
    """
    # Enforce role: only interviewer or admin can end sessions
    if user.role not in ("interviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only interviewers or admins can end sessions",
        )

    service = _get_session_service(db)

    try:
        session = await service.end_session(
            session_id=session_id,
            ended_by=user.user_id,
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except InvalidSessionStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        )

    return SessionResponse.model_validate(session)
