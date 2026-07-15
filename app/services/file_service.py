# app/services/file_service.py
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
# confirm this enum has a generic member — I assumed FILE
from app.models.enums import MediaType
from app.models.user import User
from app.repositories.file_repository import FileRepository
from app.services.storage_service import StorageService


def _infer_media_type(mime: str) -> MediaType:
    if mime.startswith("image/"):
        return MediaType.IMAGE
    if mime.startswith("video/"):
        return MediaType.VIDEO
    if mime.startswith("audio/"):
        return MediaType.AUDIO
    if "gif" in mime:
        return MediaType.GIF
    return MediaType.FILE  # <- rename to match your actual enum member


class FileService:
    @staticmethod
    def list_files(
        db: Session, user_id: str, folder_id: str | None = None
    ) -> list[Any]:
        return FileRepository.get_files(db, user_id=user_id, folder_id=folder_id)

    @staticmethod
    async def upload_file(
        db: Session,
        upload: UploadFile,
        owner: User,
        folder_id: str | None = None,
        display_name: str | None = None,
    ) -> Any:
        """Persist the uploaded bytes to disk, then record metadata."""
        stored = await StorageService.upload_file(
            file=upload, owner_id=owner.id, sub_folder="files"
        )

        return FileRepository.create(
            db,
            {
                "name": display_name or stored["original_name"],
                "original_name": stored["original_name"],
                "owner_id": owner.id,
                "folder_id": folder_id,
                "file_path": stored["file_path"],
                "url": stored["url"],
                "size_bytes": stored["size_bytes"],
                "mime_type": stored["mime_type"],
                "media_type": _infer_media_type(stored["mime_type"]),
            },
        )

    @staticmethod
    def get_file(db: Session, file_id: str, user_id: str) -> Any:
        file = FileRepository.get_user_file(
            db, file_id=file_id, user_id=user_id)
        if not file:
            raise NotFoundError("File not found")
        return file

    @staticmethod
    def move_file(
        db: Session, file_id: str, user_id: str, folder_id: str | None
    ) -> Any:
        file = FileService.get_file(db, file_id=file_id, user_id=user_id)
        return FileRepository.update(
            db, db_obj=file, update_data={"folder_id": folder_id}
        )

    @staticmethod
    def delete_file(db: Session, file_id: str, user_id: str) -> None:
        file = FileService.get_file(db, file_id=file_id, user_id=user_id)
        # also remove the bytes on disk
        StorageService.delete_file(file.file_path)
        FileRepository.delete(db, db_obj=file)
