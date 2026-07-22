"""Service layer for handling file uploads, validation, and storage routing."""

import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.constants import is_allowed_mime, max_size_mb_for
from app.models.enums import MediaType
from app.schemas.storage import UploadResult
from app.services.storage_provider import get_storage_provider


class StorageService:
    """Provides file upload and deletion capabilities with size/type validation."""

    MIME_MAP = {
        "image": "images",
        "video": "videos",
        "audio": "audio",
        "application": "files",
        "text": "files",
    }

    @staticmethod
    def _get_folder(mime: str) -> str:
        """Determine the root storage folder based on MIME type."""
        if not mime:
            return "files"
        return StorageService.MIME_MAP.get(mime.split("/")[0], "files")

    @staticmethod
    def _infer_media_type(mime: str) -> MediaType:
        """Convert a MIME type string to a standard MediaType enum."""
        if mime.startswith("image/"):
            return MediaType.IMAGE
        if mime.startswith("video/"):
            return MediaType.VIDEO
        if mime.startswith("audio/"):
            return MediaType.AUDIO
        if "gif" in mime:
            return MediaType.GIF
        return MediaType.FILE

    @staticmethod
    async def upload_file(
        file: UploadFile,
        owner_id: str,
        sub_folder: str | None = None,
    ) -> UploadResult:
        """Validate and upload a file to the configured storage provider."""

        filename = file.filename or "file"

        mime = (
            file.content_type
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        if not is_allowed_mime(mime):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {mime}",
            )

        max_size_bytes = (
            max_size_mb_for(mime) * 1024 * 1024
        )

        size_bytes = getattr(file, "size", None)

        if size_bytes is None:
            file.file.seek(0, 2)
            size_bytes = file.file.tell()
            file.file.seek(0)

        if size_bytes > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail="File exceeds maximum allowed size",
            )

        folder = (
            sub_folder
            or StorageService._get_folder(mime)
        )

        ext = Path(filename).suffix

        unique_name = (
            f"{uuid.uuid4().hex}{ext}"
        )

        storage_subfolder = (
            f"{folder}/{owner_id}"
        )

        storage = get_storage_provider()

        url = await storage.upload(
            file,
            storage_subfolder,
            unique_name,
        )

        rel_path = (
            f"{storage_subfolder}/{unique_name}"
        )

        return {
            "file_path": rel_path,
            "url": url,
            "size_bytes": size_bytes,
            "mime_type": mime,
            "original_name": filename,
            "unique_name": unique_name,
            "media_type": StorageService._infer_media_type(mime),
        }

    @staticmethod
    async def delete_file(
        path_or_url: str,
    ) -> bool:
        """Remove a file from storage."""

        try:
            storage = get_storage_provider()

            return await storage.delete(
                path_or_url
            )

        except Exception:
            return False
