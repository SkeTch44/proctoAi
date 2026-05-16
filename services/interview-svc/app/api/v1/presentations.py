"""Presentation upload and slide navigation API endpoints.

Implements:
- POST /api/v1/interviews/sessions/{session_id}/presentations — upload presentation
- GET /api/v1/interviews/sessions/{session_id}/presentations/{presentation_id} — get details
- PATCH /api/v1/interviews/sessions/{session_id}/presentations/{presentation_id} — change slide
- DELETE /api/v1/interviews/sessions/{session_id}/presentations/{presentation_id} — delete
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenUser, get_current_user
from app.core.database import get_db
from app.core.exceptions import (
    ConversionFailedError,
    FileTooLargeError,
    InvalidFileTypeError,
    InvalidSessionError,
    PermissionDeniedError,
    PresentationNotFoundError,
    ServiceUnavailableError,
    SessionNotFoundError,
)
from app.schemas.presentation import (
    PresentationResponse,
    SlideChangeRequest,
    UploadResponse,
)
from app.services.livekit_adapter import LiveKitAdapter
from app.services.presentation_service import PresentationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interviews/sessions", tags=["presentations"])


def _get_presentation_service(db: AsyncSession) -> PresentationService:
    """Build the PresentationService with its dependencies."""
    livekit = LiveKitAdapter()
    return PresentationService(db=db, livekit=livekit)


@router.post(
    "/{session_id}/presentations",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a presentation to an active session",
)
async def upload_presentation(
    session_id: str,
    file: UploadFile = File(...),
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a presentation file (.ppt, .pptx, .pdf, .key) to an active session.

    Only interviewers and interviewees can upload presentations.
    The file is converted to slide images and the previous active presentation
    is deactivated.
    """
    service = _get_presentation_service(db)

    try:
        presentation = await service.upload_presentation(
            session_id=session_id,
            file=file,
            uploaded_by=user.user_id,
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session '{session_id}' is not active",
        )
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except InvalidFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )
    except ConversionFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        )
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        )

    return UploadResponse(
        id=presentation.id,
        session_id=presentation.session_id,
        filename=presentation.filename,
        slide_count=presentation.slide_count,
        current_slide=presentation.current_slide,
        is_active=presentation.is_active,
    )


@router.get(
    "/{session_id}/presentations/{presentation_id}",
    response_model=PresentationResponse,
    summary="Get presentation details",
)
async def get_presentation(
    session_id: str,
    presentation_id: str,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific presentation within a session."""
    service = _get_presentation_service(db)
    presentation = await service.get_presentation(presentation_id)

    if presentation is None or presentation.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Presentation '{presentation_id}' not found in session '{session_id}'",
        )

    return PresentationResponse.model_validate(presentation)


@router.patch(
    "/{session_id}/presentations/{presentation_id}",
    response_model=dict,
    summary="Change the current slide of a presentation",
)
async def change_slide(
    session_id: str,
    presentation_id: str,
    body: SlideChangeRequest,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current slide index for a presentation.

    Only interviewers and interviewees can navigate slides.
    Observers are rejected with 403. The slide change is broadcast
    to all connected participants via LiveKit data channel.
    """
    service = _get_presentation_service(db)

    # Verify the presentation belongs to this session
    presentation = await service.get_presentation(presentation_id)
    if presentation is None or presentation.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Presentation '{presentation_id}' not found in session '{session_id}'",
        )

    try:
        new_slide = await service.set_current_slide(
            presentation_id=presentation_id,
            slide_index=body.slide_index,
            changed_by=user.user_id,
        )
    except PresentationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Presentation '{presentation_id}' not found or inactive",
        )
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        )

    return {
        "presentation_id": presentation_id,
        "current_slide": new_slide,
    }


@router.delete(
    "/{session_id}/presentations/{presentation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a presentation",
)
async def delete_presentation(
    session_id: str,
    presentation_id: str,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a presentation from a session.

    Only interviewers and interviewees who uploaded the presentation,
    or admins, can delete it.
    """
    service = _get_presentation_service(db)

    # Verify the presentation belongs to this session
    presentation = await service.get_presentation(presentation_id)
    if presentation is None or presentation.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Presentation '{presentation_id}' not found in session '{session_id}'",
        )

    # Only the uploader or an admin can delete
    if presentation.uploaded_by != user.user_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the uploader or an admin can delete this presentation",
        )

    try:
        await service.delete_presentation(presentation_id)
    except PresentationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Presentation '{presentation_id}' not found",
        )
