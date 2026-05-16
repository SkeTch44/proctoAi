"""Object storage abstraction for MinIO/S3 file operations."""

import logging
from io import BytesIO
from typing import BinaryIO

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """Handles file upload and retrieval from MinIO/S3-compatible object storage.

    Uses httpx with S3-compatible presigned URLs for simplicity.
    In production, this would use aioboto3 for full async S3 support.
    """

    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.S3_ENDPOINT
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket = settings.S3_BUCKET

    def _build_url(self, key: str) -> str:
        """Build the full object URL for a given storage key."""
        return f"{self.endpoint}/{self.bucket}/{key}"

    async def upload_file(self, key: str, data: BinaryIO | bytes, content_type: str = "application/octet-stream") -> str:
        """Upload a file to object storage.

        Args:
            key: The storage path/key for the file (e.g., 'interviews/{session_id}/presentations/{uuid}.pptx').
            data: File data as bytes or a file-like object.
            content_type: MIME type of the file.

        Returns:
            The URL where the file can be accessed.

        Raises:
            IOError: If the upload fails.
        """
        url = self._build_url(key)

        if isinstance(data, (bytes, bytearray)):
            file_bytes = bytes(data)
        elif isinstance(data, BytesIO):
            file_bytes = data.getvalue()
        else:
            file_bytes = data.read()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    content=file_bytes,
                    headers={
                        "Content-Type": content_type,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
        except Exception as exc:
            logger.error("Failed to upload file to '%s': %s", key, exc)
            raise IOError(f"Failed to upload file to storage: {exc}") from exc

        return url

    async def delete_file(self, key: str) -> None:
        """Delete a file from object storage.

        Args:
            key: The storage path/key of the file to delete.
        """
        url = self._build_url(key)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, timeout=30.0)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to delete file '%s': %s", key, exc)

    async def download_file(self, key: str) -> bytes:
        """Download a file from object storage.

        Args:
            key: The storage path/key of the file to download.

        Returns:
            The file content as bytes.

        Raises:
            IOError: If the download fails.
        """
        url = self._build_url(key)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=60.0)
                response.raise_for_status()
                return response.content
        except Exception as exc:
            logger.error("Failed to download file '%s': %s", key, exc)
            raise IOError(f"Failed to download file from storage: {exc}") from exc
