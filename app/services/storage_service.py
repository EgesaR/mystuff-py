import mimetypes
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from app.core.config import settings


class StorageService:
    MIME_MAP = {
        "image": "images",
        "video": "videos",
        "audio": "audio",
        "application": "files",
        "text": "files",
    }

    @staticmethod
    def _get_folder(mime: str) -> str:
        if not mime:
            return "files"
        return StorageService.MIME_MAP.get(mime.split("/")[0], "files")

    @staticmethod
    async def upload_file(
        file: UploadFile,
        owner_id: str,
        sub_folder: str | None = None,
    ) -> dict[str, Any]:

        filename = file.filename or "file"

        mime = (
            file.content_type
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        folder = sub_folder or StorageService._get_folder(mime)

        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"

        upload_dir = settings.UPLOAD_DIR or "uploads"

        rel_path = f"{folder}/{owner_id}/{unique_name}"
        abs_path = Path(upload_dir) / rel_path

        abs_path.parent.mkdir(parents=True, exist_ok=True)

        data = await file.read()

        if len(data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")

        abs_path.write_bytes(data)

        return {
            "file_path": rel_path,
            "url": f"/uploads/{rel_path}",
            "size_bytes": len(data),
            "mime_type": mime,
            "original_name": filename,
        }

    @staticmethod
    def delete_file(path: str) -> bool:
        try:
            upload_dir = settings.UPLOAD_DIR or "uploads"
            full = Path(upload_dir) / path

            if full.exists():
                full.unlink()

            return True

        except Exception:
            return False
