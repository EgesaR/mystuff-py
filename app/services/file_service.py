"""app/services/file_service.py

File management business logic engine handles object storage actions,
relational tracking, data ingestion, and file structural modifications.
"""

from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.user import User
from app.repositories.file_repository import FileRepository


class FileService:
    """Orchestrates asset lifecycle transitions and operational security."""

    @staticmethod
    def list_files(
        db: Session, user_id: str, folder_id: str | None = None
    ) -> list[Any]:
        """Fetch all workspace data catalog entries matching constraints."""
        return FileRepository.get_files(
            db, user_id=user_id, folder_id=folder_id
        )

    @staticmethod
    async def upload_file(
        db: Session,
        upload: UploadFile,
        owner: User,
        folder_id: str | None = None,
        display_name: str | None = None,
    ) -> Any:
        """Stream data payloads to store files into target storage systems."""
        final_name = display_name or upload.filename or "unnamed_file"

        return FileRepository.create(
            db,
            {
                "name": final_name,
                "owner_id": owner.id,
                "folder_id": folder_id,
                "size": upload.size or 0,
                "content_type": upload.content_type,
            },
        )

    @staticmethod
    def get_file(db: Session, file_id: str, user_id: str) -> Any:
        """Expose explicit record items verifying authorization access."""
        file = FileRepository.get_user_file(
            db, file_id=file_id, user_id=user_id
        )
        if not file:
            raise NotFoundError("File not found")
        return file

    @staticmethod
    def move_file(
        db: Session, file_id: str, user_id: str, folder_id: str | None
    ) -> Any:
        """Mutate internal path assignments mapping folder destination changes."""
        file = FileService.get_file(db, file_id=file_id, user_id=user_id)
        return FileRepository.update(
            db, db_obj=file, update_data={"folder_id": folder_id}
        )

    @staticmethod
    def delete_file(db: Session, file_id: str, user_id: str) -> None:
        """Evict record references from historical relational structures."""
        file = FileService.get_file(db, file_id=file_id, user_id=user_id)
        FileRepository.delete(db, db_obj=file)
