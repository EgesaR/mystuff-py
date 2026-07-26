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
        """Retrieve files.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            folder_id (str | None): Unique identifier of the folder.
        
        Returns:
            list[File]: List of File.
        """
        query = db.query(cls.model).filter(cls.model.owner_id == user_id)
        if folder_id is not None:
            query = query.filter(cls.model.folder_id == folder_id)
        return query.all()

    @classmethod
    def get_user_files(cls, db: Session, user_id: str) -> list[File]:
        """Retrieve user files.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[File]: List of File.
        """
        return (
            db.query(cls.model)
            .filter(cls.model.owner_id == user_id)
            .all()
        )

    @classmethod
    def get_folder_files(
        cls, db: Session, user_id: str, folder_id: str
    ) -> list[File]:
        """Retrieve folder files.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            folder_id (str): Unique identifier of the folder.
        
        Returns:
            list[File]: List of File.
        """
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
        """Search files.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            query (str): Query string.
        
        Returns:
            list[File]: List of File.
        """
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
        """Retrieve user file.
        
        Args:
            db (Session): Database session.
            file_id (str): Unique identifier of the file.
            user_id (str): Unique identifier of the user.
        
        Returns:
            File | None: File or None.
        """
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
        """File exists.
        
        Args:
            db (Session): Database session.
            file_id (str): Unique identifier of the file.
            user_id (str): Unique identifier of the user.
        
        Returns:
            bool: True if successful, False otherwise.
        """
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
        """Retrieve by name in folder.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            folder_id (str | None): Unique identifier of the folder.
            name (str): Name string.
        
        Returns:
            File | None: File or None.
        """
        query = db.query(cls.model).filter(
            cls.model.owner_id == user_id,
            cls.model.name == name,
        )

        query = query.filter(cls.model.folder_id.is_(None)) if folder_id is None else query.filter(cls.model.folder_id == folder_id)

        return query.first()
