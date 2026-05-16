"""Presentation service — handles file upload, conversion, and slide synchronization."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    ConversionFailedError,
    FileTooLargeError,
    InvalidFileTypeError,
    InvalidSessionError,
    PermissionDeniedError,
    PresentationNotFoundError,
    SessionNotFoundError,
    SlideIndexOutOfBoundsError,
)
from app.models.interview_session import InterviewSession
from app.models.participant import SessionParticipant
from app.models.presentation import Presentation
from app.services.file_converter import convert_to_slides
from app.services.livekit_adapter import LiveKitAdapter
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

# Allowed file extensions and their expected MIME types
ALLOWED_EXTENSIONS = {".ppt", ".pptx", ".pdf", ".key"}

EXTENSION_MIME_MAP = {
    ".ppt": {"application/vnd.ms-powerpoint"},
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },
    ".pdf": {"application/pdf"},
    ".key": {"application/x-iwork-keynote-sffkey", "application/octet-stream"},
}


class PresentationService:
    """Handles presentation upload, conversion, and slide synchronization.

    Responsibilities:
    - Accept PPT/PDF uploads and store in object storage
    - Convert presentations to slide images (LibreOffice headless or pdf2image)
    - Track current slide position per session
    - Broadcast slide changes via LiveKit data channels
    """

    def __init__(
        self,
        db: AsyncSession,
        livekit: LiveKitAdapter,
        storage: StorageService | None = None,
    ):
        self.db = db
        self.livekit = livekit
        self.storage = storage or StorageService()
        self._settings = get_settings()

    async def upload_presentation(
        self,
        session_id: str,
        file: UploadFile,
        uploaded_by: int,
    ) -> Presentation:
        """Upload a presentation file, convert to slides, and notify participants.

        Follows the design's upload algorithm:
        1. Validate session exists and is active
        2. Validate caller is interviewer or interviewee
        3. Validate file extension and MIME type
        4. Validate file size ≤ 50MB
        5. Store original file in MinIO/S3
        6. Convert to slide images
        7. Deactivate previous active presentation
        8. Create Presentation record with slide URLs
        9. Notify all participants via LiveKit data channel

        Args:
            session_id: The active session to upload the presentation to.
            file: The uploaded file (FastAPI UploadFile).
            uploaded_by: User ID of the uploader.

        Returns:
            The created Presentation record.

        Raises:
            SessionNotFoundError: If session does not exist.
            InvalidSessionError: If session is not in "active" status.
            PermissionDeniedError: If caller is not interviewer or interviewee.
            InvalidFileTypeError: If file extension or MIME type is invalid.
            FileTooLargeError: If file exceeds 50MB.
            ConversionFailedError: If file conversion fails or times out.
        """
        # Step 1: Validate session exists and is active
        result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError(session_id)

        if session.status != "active":
            raise InvalidSessionError(session_id)

        # Step 2: Validate caller is interviewer or interviewee
        participant_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == uploaded_by,
                SessionParticipant.status == "connected",
            )
        )
        participant = participant_result.scalar_one_or_none()

        if participant is None or participant.role not in ("interviewer", "interviewee"):
            raise PermissionDeniedError(
                "Only interviewers and interviewees can upload presentations."
            )

        # Step 3: Validate file extension
        filename = file.filename or ""
        ext = Path(filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidFileTypeError(ext, ALLOWED_EXTENSIONS)

        # Validate MIME type matches extension
        content_type = file.content_type or "application/octet-stream"
        expected_mimes = EXTENSION_MIME_MAP.get(ext, set())
        if content_type not in expected_mimes and content_type != "application/octet-stream":
            raise InvalidFileTypeError(
                ext,
                ALLOWED_EXTENSIONS,
            )

        # Step 4: Validate file size ≤ 50MB
        max_size = self._settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        file_data = await file.read()
        file_size = len(file_data)

        if file_size > max_size:
            raise FileTooLargeError(file_size, max_size)

        # Step 5: Store original file in MinIO/S3
        file_uuid = str(uuid4())
        storage_key = f"interviews/{session_id}/presentations/{file_uuid}{ext}"
        file_url = await self.storage.upload_file(
            key=storage_key,
            data=file_data,
            content_type=content_type,
        )

        # Step 6: Convert to slide images
        try:
            slide_images = await convert_to_slides(file_data, ext)
        except asyncio.TimeoutError:
            raise ConversionFailedError(
                f"File conversion timed out after 120 seconds. "
                f"The original file has been retained. You may retry the upload or use screen sharing."
            )
        except Exception as exc:
            raise ConversionFailedError(
                f"File conversion failed: {exc}. "
                f"The original file has been retained. You may retry the upload or use screen sharing."
            )

        # Upload slide images to storage
        slide_urls = []
        for i, slide_image in enumerate(slide_images):
            slide_key = f"interviews/{session_id}/slides/{file_uuid}_{i}.png"
            slide_url = await self.storage.upload_file(
                key=slide_key,
                data=slide_image,
                content_type="image/png",
            )
            slide_urls.append(slide_url)

        # Step 7: Deactivate previous active presentation(s) for this session
        await self.db.execute(
            update(Presentation)
            .where(
                Presentation.session_id == session_id,
                Presentation.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )

        # Step 8: Create Presentation record
        presentation = Presentation(
            id=str(uuid4()),
            session_id=session_id,
            filename=filename,
            file_url=file_url,
            slide_count=len(slide_urls),
            current_slide=0,
            slides_json=json.dumps(slide_urls),
            uploaded_by=uploaded_by,
            is_active=True,
        )
        self.db.add(presentation)
        await self.db.commit()

        # Step 9: Notify all participants via LiveKit data channel
        try:
            await self.livekit.send_data(
                room_name=session.room_name,
                data=json.dumps({
                    "type": "presentation_loaded",
                    "presentation_id": presentation.id,
                    "slide_count": len(slide_urls),
                    "current_slide": 0,
                }),
            )
        except Exception as exc:
            # Non-fatal: log but don't fail the upload
            logger.warning(
                "Failed to notify participants of new presentation: %s", exc
            )

        return presentation

    async def get_presentation(
        self,
        presentation_id: str,
    ) -> Optional[Presentation]:
        """Retrieve a presentation by its ID.

        Args:
            presentation_id: The presentation ID to look up.

        Returns:
            The Presentation record if found, or None.
        """
        result = await self.db.execute(
            select(Presentation).where(Presentation.id == presentation_id)
        )
        return result.scalar_one_or_none()

    async def set_current_slide(
        self,
        presentation_id: str,
        slide_index: int,
        changed_by: int,
    ) -> int:
        """Change the current slide of a presentation and broadcast to participants.

        Validates:
        - Presentation exists and is active
        - slide_index is within [0, slide_count - 1]
        - Caller has interviewer or interviewee role (observers rejected)

        Applies last-write-wins ordering based on server-side receipt time.

        Args:
            presentation_id: The presentation to navigate.
            slide_index: The target slide index.
            changed_by: User ID of the person changing the slide.

        Returns:
            The new current_slide value.

        Raises:
            PresentationNotFoundError: If presentation does not exist or is inactive.
            PermissionDeniedError: If caller is an observer.
            ValueError: If slide_index is out of bounds.
        """
        result = await self.db.execute(
            select(Presentation).where(
                Presentation.id == presentation_id,
                Presentation.is_active == True,  # noqa: E712
            )
        )
        presentation = result.scalar_one_or_none()

        if presentation is None:
            raise PresentationNotFoundError(presentation_id)

        # Validate caller role
        participant_result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == presentation.session_id,
                SessionParticipant.user_id == changed_by,
                SessionParticipant.status == "connected",
            )
        )
        participant = participant_result.scalar_one_or_none()

        if participant is None or participant.role not in ("interviewer", "interviewee"):
            raise PermissionDeniedError(
                "Only interviewers and interviewees can navigate slides."
            )

        # Validate slide_index bounds
        if slide_index < 0 or slide_index >= presentation.slide_count:
            raise ValueError(
                f"slide_index {slide_index} is out of bounds "
                f"[0, {presentation.slide_count - 1}]."
            )

        # Update current_slide (last-write-wins)
        presentation.current_slide = slide_index
        await self.db.commit()

        # Broadcast slide change via LiveKit data channel
        try:
            session_result = await self.db.execute(
                select(InterviewSession).where(
                    InterviewSession.id == presentation.session_id
                )
            )
            session = session_result.scalar_one_or_none()
            if session:
                await self.livekit.send_data(
                    room_name=session.room_name,
                    data=json.dumps({
                        "type": "slide_change",
                        "presentation_id": presentation_id,
                        "slide_index": slide_index,
                    }),
                )
        except Exception as exc:
            # Non-fatal: log but don't fail the slide change
            logger.warning(
                "Failed to broadcast slide change for presentation '%s': %s",
                presentation_id,
                exc,
            )

        return slide_index

    async def delete_presentation(
        self,
        presentation_id: str,
    ) -> None:
        """Delete a presentation record and its associated files.

        Args:
            presentation_id: The ID of the presentation to delete.

        Raises:
            PresentationNotFoundError: If the presentation does not exist.
        """
        result = await self.db.execute(
            select(Presentation).where(Presentation.id == presentation_id)
        )
        presentation = result.scalar_one_or_none()

        if presentation is None:
            raise PresentationNotFoundError(presentation_id)

        # Attempt to delete the original file from storage
        if presentation.file_url:
            try:
                # Extract the key from the URL
                key = self._extract_key_from_url(presentation.file_url)
                if key:
                    await self.storage.delete_file(key)
            except Exception as exc:
                logger.warning(
                    "Failed to delete original file for presentation '%s': %s",
                    presentation_id,
                    exc,
                )

        # Attempt to delete slide images from storage
        if presentation.slides_json:
            try:
                slide_urls = json.loads(presentation.slides_json)
                for slide_url in slide_urls:
                    key = self._extract_key_from_url(slide_url)
                    if key:
                        await self.storage.delete_file(key)
            except Exception as exc:
                logger.warning(
                    "Failed to delete slide images for presentation '%s': %s",
                    presentation_id,
                    exc,
                )

        # Delete the database record
        await self.db.delete(presentation)
        await self.db.commit()

    def _extract_key_from_url(self, url: str) -> Optional[str]:
        """Extract the storage key from a full object URL.

        The URL format is: {endpoint}/{bucket}/{key}
        """
        prefix = f"{self._settings.S3_ENDPOINT}/{self._settings.S3_BUCKET}/"
        if url.startswith(prefix):
            return url[len(prefix):]
        return None
