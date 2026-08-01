# app/services/file_service.py
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.user import User
from app.repositories.file_repository import FileRepository
from app.services.storage_service import StorageService


class FileService:
    @staticmethod
    def list_files(
        db: Session, user_id: str, folder_id: str | None = None
    ) -> list[Any]:
        """List files.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            folder_id (str | None): Unique identifier of the folder.

        Returns:
            list[Any]: List of Any.
        """
        return FileRepository.get_files(db, user_id=user_id, folder_id=folder_id)

    @staticmethod
    async def upload_file(
        db: Session,
        upload: UploadFile,
        owner: User,
        folder_id: str | None = None,
        display_name: str | None = None,
    ) -> Any:
        """Upload file.

        Args:
            db (Session): Database session.
            upload (UploadFile): The upload.
            owner (User): The owner.
            folder_id (str | None): Unique identifier of the folder.
            display_name (str | None): The display name.

        Returns:
            Any: Result value.
        """
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
        """Retrieve file.

        Args:
            db (Session): Database session.
            file_id (str): Unique identifier of the file.
            user_id (str): Unique identifier of the user.

        Returns:
            Any: Result value.
        """
        file = FileRepository.get_user_file(
            db, file_id=file_id, user_id=user_id)
        if not file:
            raise NotFoundError("File not found")
        if file.owner_id != user_id:
            from app.models.enums import ShareResourceType
            from app.services.share_service import ShareService
            if not ShareService.has_access(db, ShareResourceType.FILE, file_id, user_id):
                raise PermissionDeniedError("Access denied")
        return file

    @staticmethod
    def move_file(
        db: Session, file_id: str, user_id: str, folder_id: str | None
    ) -> Any:
        """Move file.

        Args:
            db (Session): Database session.
            file_id (str): Unique identifier of the file.
            user_id (str): Unique identifier of the user.
            folder_id (str | None): Unique identifier of the folder.

        Returns:
            Any: Result value.
        """
        file = FileService.get_file(db, file_id=file_id, user_id=user_id)
        return FileRepository.update(
            db, db_obj=file, update_data={"folder_id": folder_id}
        )

    @staticmethod
    async def delete_file(db: Session, file_id: str, user_id: str) -> None:
        """Delete file.

        Args:
            db (Session): Database session.
            file_id (str): Unique identifier of the file.
            user_id (str): Unique identifier of the user.

        Returns:
            None: None result.
        """
        file = FileService.get_file(db, file_id=file_id, user_id=user_id)

        # Pass the url (or file_path) based on how you implemented storage.delete()
        await StorageService.delete_file(file.url)
        FileRepository.delete(db, db_obj=file)
