"""app/services/folder_service.py

Folder business logic controller processing tree hierarchies and metadata.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.repositories.folder_repository import FolderRepository


class FolderService:
    """Manages lifecycle and hierarchical operations for directory folders."""

    @staticmethod
    def create_folder(
        db: Session,
        user_id: str,
        name: str,
        color: str | None = None,
        parent_id: str | None = None,
    ) -> Any:
        """Validate naming constraints and instantiate a target folder."""
        existing = FolderRepository.get_folder_by_name(
            db, name, user_id, parent_id
        )

        if existing:
            raise ValueError("Folder already exists")

        return FolderRepository.create(
            db,
            {
                "name": name,
                "owner_id": user_id,
                "parent_id": parent_id,
                "color": color,
            },
        )

    @staticmethod
    def list_folders(
        db: Session, user_id: str, parent_id: str | None = None
    ) -> list[Any]:
        """Retrieve scoped folders matching identities and hierarchies."""
        return FolderRepository.get_folders(
            db, user_id=user_id, parent_id=parent_id
        )

    @staticmethod
    def update_folder(
        db: Session, folder_id: str, user_id: str, data: dict[str, Any]
    ) -> Any:
        """Modify styling or metadata attributes of an existing folder."""
        folder = FolderRepository.get_user_folder(
            db, folder_id=folder_id, user_id=user_id
        )
        if not folder:
            raise NotFoundError("Folder not found")
        return FolderRepository.update(
            db, db_obj=folder, update_data=data
        )

    @staticmethod
    def delete_folder(db: Session, folder_id: str, user_id: str) -> None:
        """Remove a folder resource cascading entity drops downward."""
        folder = FolderRepository.get_user_folder(
            db, folder_id=folder_id, user_id=user_id
        )
        if not folder:
            raise NotFoundError("Folder not found")
        FolderRepository.delete(db, db_obj=folder)

    @staticmethod
    def get_user_folders(db: Session, user_id: str) -> list[Any]:
        """Fetch flat catalogs belonging directly to an account profile."""
        return FolderRepository.get_user_folders(db, user_id)

    @staticmethod
    def get_folder_tree(db: Session, folder_id: str, user_id: str) -> Any:
        """Construct and structuralize recursive nested folder trees."""
        folder = FolderRepository.get_user_folder(
            db, folder_id=folder_id, user_id=user_id
        )
        if not folder:
            raise NotFoundError("Folder not found")
        return folder
