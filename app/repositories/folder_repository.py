"""Module containing the repository layer for Folder model operations."""

from sqlalchemy.orm import Session

from app.models.folder import Folder
from app.repositories.base_repository import BaseRepository


class FolderRepository(BaseRepository[Folder]):
    """Repository for managing database actions for Folder entities."""

    model = Folder

    @classmethod
    def get_user_folders(
        cls,
        db: Session,
        user_id: str,
    ) -> list[Folder]:
        """Retrieve user folders.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[Folder]: List of Folder.
        """
        return (
            db.query(cls.model)
            .filter(cls.model.owner_id == user_id)
            .all()
        )

    @classmethod
    def get_root_folders(
        cls,
        db: Session,
        user_id: str,
    ) -> list[Folder]:
        """Retrieve root folders.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[Folder]: List of Folder.
        """
        return (
            db.query(cls.model)
            .filter(
                cls.model.owner_id == user_id,
                cls.model.parent_id.is_(None),
            )
            .all()
        )

    @classmethod
    def get_folders(
        cls,
        db: Session,
        user_id: str,
        parent_id: str | None = None,
    ) -> list[Folder]:
        """Retrieve folders.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            parent_id (str | None): Unique identifier of the target resource.
        
        Returns:
            list[Folder]: List of Folder.
        """
        if parent_id is None:
            return cls.get_root_folders(db, user_id)
        return (
            db.query(cls.model)
            .filter(
                cls.model.owner_id == user_id,
                cls.model.parent_id == parent_id,
            )
            .all()
        )

    @classmethod
    def get_by_parent(
        cls,
        db: Session,
        parent_id: str,
    ) -> list[Folder]:
        """Retrieve by parent.
        
        Args:
            db (Session): Database session.
            parent_id (str): Unique identifier of the target resource.
        
        Returns:
            list[Folder]: List of Folder.
        """
        return (
            db.query(cls.model)
            .filter(cls.model.parent_id == parent_id)
            .all()
        )

    @classmethod
    def get_user_folder(
        cls,
        db: Session,
        folder_id: str,
        user_id: str,
    ) -> Folder | None:
        """Retrieve user folder.
        
        Args:
            db (Session): Database session.
            folder_id (str): Unique identifier of the folder.
            user_id (str): Unique identifier of the user.
        
        Returns:
            Folder | None: Folder or None.
        """
        return (
            db.query(cls.model)
            .filter(
                cls.model.id == folder_id,
                cls.model.owner_id == user_id,
            )
            .first()
        )

    @classmethod
    def folder_exists(
        cls,
        db: Session,
        folder_id: str,
        user_id: str,
    ) -> bool:
        """Folder exists.
        
        Args:
            db (Session): Database session.
            folder_id (str): Unique identifier of the folder.
            user_id (str): Unique identifier of the user.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        return (
            db.query(cls.model)
            .filter(
                cls.model.id == folder_id,
                cls.model.owner_id == user_id,
            )
            .first()
            is not None
        )

    @classmethod
    def get_folder_by_name(
        cls,
        db: Session,
        name: str,
        user_id: str,
        parent_id: str | None = None,
    ) -> Folder | None:
        """Retrieve folder by name.
        
        Args:
            db (Session): Database session.
            name (str): Name string.
            user_id (str): Unique identifier of the user.
            parent_id (str | None): Unique identifier of the target resource.
        
        Returns:
            Folder | None: Folder or None.
        """
        query = db.query(cls.model).filter(
            cls.model.name == name,
            cls.model.owner_id == user_id,
        )

        query = query.filter(cls.model.parent_id.is_(None)) if parent_id is None else query.filter(cls.model.parent_id == parent_id)

        return query.first()
