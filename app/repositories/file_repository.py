"""app/repositories/file_repository.py

Data access layer for File database entities handling relational operations.
"""

from sqlalchemy.orm import Session

from app.models.file import File
from app.repositories.base_repository import BaseRepository


class FileRepository(BaseRepository[File]):
    """Handles database persistence and specialized queries for File records."""

    model = File

    @classmethod
    def get_files(
        cls, db: Session, *, user_id: str, folder_id: str | None = None
    ) -> list[File]:
        """Retrieve files belonging to a user, optionally filtered by folder."""
        query = db.query(cls.model).filter(cls.model.owner_id == user_id)
        if folder_id is not None:
            query = query.filter(cls.model.folder_id == folder_id)
        return query.all()

    @classmethod
    def get_user_files(cls, db: Session, user_id: str) -> list[File]:
        """Retrieve all files associated with a specific owner ID."""
        return (
            db.query(cls.model)
            .filter(cls.model.owner_id == user_id)
            .all()
        )

    @classmethod
    def get_folder_files(
        cls, db: Session, user_id: str, folder_id: str
    ) -> list[File]:
        """Fetch files inside a specific folder matching owner identity."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.folder_id == folder_id,
                cls.model.owner_id == user_id,
            )
            .all()
        )

    @classmethod
    def search_files(
        cls, db: Session, user_id: str, query: str
    ) -> list[File]:
        """Perform a case-insensitive sub-string match query on file names."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.owner_id == user_id,
                cls.model.name.ilike(f"%{query}%"),
            )
            .all()
        )

    @classmethod
    def get_user_file(
        cls, db: Session, file_id: str, user_id: str
    ) -> File | None:
        """Fetch a distinct file resource checking owner validation constraints."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.id == file_id,
                cls.model.owner_id == user_id,
            )
            .first()
        )

    @classmethod
    def file_exists(cls, db: Session, file_id: str, user_id: str) -> bool:
        """Determine existential status of a file using identity parameters."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.id == file_id,
                cls.model.owner_id == user_id,
            )
            .first()
            is not None
        )

    @classmethod
    def get_by_name_in_folder(
        cls,
        db: Session,
        *,
        user_id: str,
        folder_id: str | None,
        name: str,
    ) -> File | None:
        """Locate file matching specific naming inside a targeted directory."""
        query = db.query(cls.model).filter(
            cls.model.owner_id == user_id,
            cls.model.name == name,
        )

        if folder_id is None:
            query = query.filter(cls.model.folder_id.is_(None))
        else:
            query = query.filter(cls.model.folder_id == folder_id)

        return query.first()
