# app/services/file_service.py
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.user import User
from app.repositories.file_repository import FileRepository
from app.services.storage_service import StorageService


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

        stored = await StorageService.upload_file(
            file=upload, owner_id=owner.id
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
                "media_type": stored["media_type"],
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
    async def delete_file(db: Session, file_id: str, user_id: str) -> None:
        """Now async because cloud deletion requires a network request."""
        file = FileService.get_file(db, file_id=file_id, user_id=user_id)

        # Pass the url (or file_path) based on how you implemented storage.delete()
        await StorageService.delete_file(file.url)
        FileRepository.delete(db, db_obj=file)
