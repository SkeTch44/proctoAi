"""FastAPI exception handlers for interview-svc.

Maps custom domain exceptions to structured HTTP error responses.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ConversionFailedError,
    DuplicateIntervieweeError,
    DuplicateParticipantError,
    FileTooLargeError,
    InvalidFileTypeError,
    InvalidRoleError,
    InvalidSessionError,
    InvalidSessionStateError,
    ParticipantRemovedError,
    PermissionDeniedError,
    PresentationNotFoundError,
    ServiceUnavailableError,
    SessionEndedError,
    SessionFullError,
    SessionNotFoundError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(SessionNotFoundError)
    async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": "session_not_found", "detail": str(exc)},
        )

    @app.exception_handler(SessionFullError)
    async def session_full_handler(request: Request, exc: SessionFullError):
        return JSONResponse(
            status_code=409,
            content={"error": "session_full", "detail": str(exc)},
        )

    @app.exception_handler(SessionEndedError)
    async def session_ended_handler(request: Request, exc: SessionEndedError):
        return JSONResponse(
            status_code=409,
            content={"error": "session_ended", "detail": str(exc)},
        )

    @app.exception_handler(DuplicateIntervieweeError)
    async def duplicate_interviewee_handler(
        request: Request, exc: DuplicateIntervieweeError
    ):
        return JSONResponse(
            status_code=409,
            content={"error": "duplicate_interviewee", "detail": str(exc)},
        )

    @app.exception_handler(DuplicateParticipantError)
    async def duplicate_participant_handler(
        request: Request, exc: DuplicateParticipantError
    ):
        return JSONResponse(
            status_code=409,
            content={"error": "duplicate_participant", "detail": str(exc)},
        )

    @app.exception_handler(ParticipantRemovedError)
    async def participant_removed_handler(
        request: Request, exc: ParticipantRemovedError
    ):
        return JSONResponse(
            status_code=403,
            content={"error": "participant_removed", "detail": str(exc)},
        )

    @app.exception_handler(InvalidSessionStateError)
    async def invalid_session_state_handler(
        request: Request, exc: InvalidSessionStateError
    ):
        return JSONResponse(
            status_code=409,
            content={"error": "invalid_state_transition", "detail": str(exc)},
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        return JSONResponse(
            status_code=403,
            content={"error": "permission_denied", "detail": str(exc)},
        )

    @app.exception_handler(InvalidRoleError)
    async def invalid_role_handler(request: Request, exc: InvalidRoleError):
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_role", "detail": str(exc)},
        )

    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_handler(
        request: Request, exc: ServiceUnavailableError
    ):
        return JSONResponse(
            status_code=503,
            content={
                "error": "service_unavailable",
                "detail": str(exc),
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(FileTooLargeError)
    async def file_too_large_handler(request: Request, exc: FileTooLargeError):
        return JSONResponse(
            status_code=413,
            content={"error": "file_too_large", "detail": str(exc)},
        )

    @app.exception_handler(InvalidFileTypeError)
    async def invalid_file_type_handler(request: Request, exc: InvalidFileTypeError):
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_file_type", "detail": str(exc)},
        )

    @app.exception_handler(ConversionFailedError)
    async def conversion_failed_handler(request: Request, exc: ConversionFailedError):
        return JSONResponse(
            status_code=422,
            content={"error": "conversion_failed", "detail": exc.detail},
        )

    @app.exception_handler(PresentationNotFoundError)
    async def presentation_not_found_handler(
        request: Request, exc: PresentationNotFoundError
    ):
        return JSONResponse(
            status_code=404,
            content={"error": "presentation_not_found", "detail": str(exc)},
        )

    @app.exception_handler(InvalidSessionError)
    async def invalid_session_handler(request: Request, exc: InvalidSessionError):
        return JSONResponse(
            status_code=409,
            content={"error": "invalid_session", "detail": str(exc)},
        )
