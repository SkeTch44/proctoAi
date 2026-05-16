"""Custom exception classes for interview-svc."""


class InterviewServiceError(Exception):
    """Base exception for interview service errors."""

    pass


class ServiceUnavailableError(InterviewServiceError):
    """Raised when an external service (e.g., LiveKit) is unreachable or times out."""

    def __init__(self, service: str = "LiveKit", retry_after: int = 5):
        self.service = service
        self.retry_after = retry_after
        super().__init__(f"{service} is unavailable. Retry after {retry_after}s.")


class SessionNotFoundError(InterviewServiceError):
    """Raised when a session cannot be found."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' not found.")


class SessionFullError(InterviewServiceError):
    """Raised when a session has reached its participant limit."""

    def __init__(self, session_id: str, max_participants: int):
        self.session_id = session_id
        self.max_participants = max_participants
        super().__init__(
            f"Session '{session_id}' is full (max {max_participants} participants)."
        )


class SessionEndedError(InterviewServiceError):
    """Raised when attempting to join an ended session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' has ended.")


class DuplicateIntervieweeError(InterviewServiceError):
    """Raised when a second interviewee tries to join a session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' already has an interviewee.")


class InvalidRoleError(InterviewServiceError):
    """Raised when an invalid participant role is provided."""

    def __init__(self, role: str):
        self.role = role
        super().__init__(
            f"Invalid role '{role}'. Must be one of: interviewer, interviewee, observer."
        )


class InvalidSessionStateError(InterviewServiceError):
    """Raised when a session state transition is invalid."""

    def __init__(self, current_status: str, target_status: str):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition from '{current_status}' to '{target_status}'."
        )


class DuplicateParticipantError(InterviewServiceError):
    """Raised when a user tries to join a session they're already connected to."""

    def __init__(self, session_id: str, user_id: int):
        self.session_id = session_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} is already connected to session '{session_id}'."
        )


class ParticipantRemovedError(InterviewServiceError):
    """Raised when a removed participant tries to rejoin."""

    def __init__(self, session_id: str, user_id: int):
        self.session_id = session_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} was removed from session '{session_id}' and cannot rejoin."
        )


class PermissionDeniedError(InterviewServiceError):
    """Raised when a user lacks permission for an action."""

    def __init__(self, message: str = "Permission denied."):
        super().__init__(message)


class InvalidSessionError(InterviewServiceError):
    """Raised when a session is not in a valid state for the requested operation."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"Session '{session_id}' is not active or does not exist."
        )


class FileTooLargeError(InterviewServiceError):
    """Raised when an uploaded file exceeds the maximum allowed size."""

    def __init__(self, file_size: int, max_size: int):
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(
            f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)."
        )


class InvalidFileTypeError(InterviewServiceError):
    """Raised when an uploaded file has a disallowed extension or MIME type."""

    def __init__(self, extension: str, allowed: set[str] | None = None):
        self.extension = extension
        self.allowed = allowed
        allowed_str = ", ".join(sorted(allowed)) if allowed else "unknown"
        super().__init__(
            f"File extension '{extension}' is not allowed. Allowed: {allowed_str}"
        )


class ConversionFailedError(InterviewServiceError):
    """Raised when presentation file conversion fails or times out."""

    def __init__(self, detail: str = "File conversion failed."):
        self.detail = detail
        super().__init__(detail)


class PresentationNotFoundError(InterviewServiceError):
    """Raised when a presentation cannot be found."""

    def __init__(self, presentation_id: str):
        self.presentation_id = presentation_id
        super().__init__(f"Presentation '{presentation_id}' not found.")


class SlideIndexOutOfBoundsError(InterviewServiceError):
    """Raised when a slide index is outside the valid range [0, slide_count-1]."""

    def __init__(self, slide_index: int, slide_count: int):
        self.slide_index = slide_index
        self.slide_count = slide_count
        super().__init__(
            f"Slide index {slide_index} is out of bounds. "
            f"Valid range: [0, {slide_count - 1}]."
        )
