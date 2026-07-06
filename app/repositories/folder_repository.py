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
        """Retrieve all folders belonging to a specified user account."""
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
        """Retrieve all top-level (root) folders for a specific user."""
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
        """List folders filtered by user ownership and parent ID state."""
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
        """Fetch all subfolders tied directly to a parent folder ID."""
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
        """Retrieve a specific folder validating identity ownership."""
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
        """Check existence of a folder constrained by owner identity."""
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
        """Locate a folder by name matching specified depth profiles."""
        query = db.query(cls.model).filter(
            cls.model.name == name,
            cls.model.owner_id == user_id,
        )

        if parent_id is None:
            query = query.filter(cls.model.parent_id.is_(None))
        else:
            query = query.filter(cls.model.parent_id == parent_id)

        return query.first()
