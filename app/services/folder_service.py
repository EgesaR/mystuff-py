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
        """Create folder.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            name (str): Name string.
            color (str | None): The color.
            parent_id (str | None): Unique identifier of the target resource.
        
        Returns:
            Any: Result value.
        """
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
        """List folders.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            parent_id (str | None): Unique identifier of the target resource.
        
        Returns:
            list[Any]: List of Any.
        """
        return FolderRepository.get_folders(
            db, user_id=user_id, parent_id=parent_id
        )

    @staticmethod
    def update_folder(
        db: Session, folder_id: str, user_id: str, data: dict[str, Any]
    ) -> Any:
        """Update folder.
        
        Args:
            db (Session): Database session.
            folder_id (str): Unique identifier of the folder.
            user_id (str): Unique identifier of the user.
            data (dict[str, Any]): The data.
        
        Returns:
            Any: Result value.
        """
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
        """Delete folder.
        
        Args:
            db (Session): Database session.
            folder_id (str): Unique identifier of the folder.
            user_id (str): Unique identifier of the user.
        
        Returns:
            None: None result.
        """
        folder = FolderRepository.get_user_folder(
            db, folder_id=folder_id, user_id=user_id
        )
        if not folder:
            raise NotFoundError("Folder not found")
        FolderRepository.delete(db, db_obj=folder)

    @staticmethod
    def get_user_folders(db: Session, user_id: str) -> list[Any]:
        """Retrieve user folders.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[Any]: List of Any.
        """
        return FolderRepository.get_user_folders(db, user_id)

    @staticmethod
    def get_folder_tree(db: Session, folder_id: str, user_id: str) -> Any:
        """Retrieve folder tree.
        
        Args:
            db (Session): Database session.
            folder_id (str): Unique identifier of the folder.
            user_id (str): Unique identifier of the user.
        
        Returns:
            Any: Result value.
        """
        folder = FolderRepository.get_user_folder(
            db, folder_id=folder_id, user_id=user_id
        )
        if not folder:
            raise NotFoundError("Folder not found")
        return folder
