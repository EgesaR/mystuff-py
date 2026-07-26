"""Base repository class for generic CRUD operations."""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.base import Base

# Renamed to ModelT to satisfy Pylint C0103 (Type variable naming)
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository[ModelT]:
    """Base repository providing common database operations."""

    model: type[ModelT]

    @classmethod
    def get(cls, db: Session, object_id: UUID | str) -> ModelT | None:
        """Retrieve.
        
        Args:
            db (Session): Database session.
            object_id (UUID | str): Unique identifier of the target resource.
        
        Returns:
            ModelT | None: ModelT or None.
        """
        return db.query(cls.model).filter(cls.model.id == object_id).first()  # type: ignore

    @classmethod
    def get_all(cls, db: Session, skip: int = 0, limit: int = 100) -> list[ModelT]:
        """Retrieve all.
        
        Args:
            db (Session): Database session.
            skip (int): Skip integer.
            limit (int): Limit integer.
        
        Returns:
            list[ModelT]: List of ModelT.
        """
        return db.query(cls.model).offset(skip).limit(limit).all()

    @classmethod
    def create(cls, db: Session, obj_in: dict[str, Any]) -> ModelT:
        """Create.
        
        Args:
            db (Session): Database session.
            obj_in (dict[str, Any]): The obj in.
        
        Returns:
            ModelT: ModelT result.
        """
        db_obj = cls.model(**obj_in)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception:
            db.rollback()
            raise

    @classmethod
    def update(
        cls, db: Session, db_obj: ModelT, update_data: dict[str, Any]
    ) -> ModelT:
        """Update.
        
        Args:
            db (Session): Database session.
            db_obj (ModelT): The db obj.
            update_data (dict[str, Any]): The update data.
        
        Returns:
            ModelT: ModelT result.
        """
        try:
            for field, value in update_data.items():
                setattr(db_obj, field, value)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception:
            db.rollback()
            raise

    @classmethod
    def delete(cls, db: Session, db_obj: ModelT) -> None:
        """Delete.
        
        Args:
            db (Session): Database session.
            db_obj (ModelT): The db obj.
        
        Returns:
            None: None result.
        """
        try:
            db.delete(db_obj)
            db.commit()
        except Exception:
            db.rollback()
            raise

    @classmethod
    def exists(cls, db: Session, object_id: UUID | str) -> bool:
        """Exists.
        
        Args:
            db (Session): Database session.
            object_id (UUID | str): Unique identifier of the target resource.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        return (
            db.query(cls.model.id)  # type: ignore
            .filter(cls.model.id == object_id)  # type: ignore
            .limit(1)
            .scalar()
            is not None
        )

    @classmethod
    def count(cls, db: Session) -> int:
        """Count.
        
        Args:
            db (Session): Database session.
        
        Returns:
            int: int result.
        """
        # pylint: disable=not-callable
        return db.query(func.count(cls.model.id)).scalar() or 0  # type: ignore
