"""Repository for system logging operations."""

from sqlalchemy.orm import Session

from app.models.enums import LogLevel
from app.models.system_log import SystemLog
from app.repositories.base_repository import BaseRepository


# pylint: disable=too-few-public-methods
class LogRepository(BaseRepository[SystemLog]):
    """Repository for managing system logs."""

    model = SystemLog

    @classmethod
    def get_by_level(cls, db: Session, level: LogLevel) -> list[SystemLog]:
        """Retrieve by level.
        
        Args:
            db (Session): Database session.
            level (LogLevel): The level.
        
        Returns:
            list[SystemLog]: List of SystemLog.
        """
        return db.query(cls.model).filter(cls.model.level == level).all()

    @classmethod
    def get_user_logs(
        cls, db: Session, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[SystemLog]:
        """Retrieve user logs.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            skip (int): Skip integer.
            limit (int): Limit integer.
        
        Returns:
            list[SystemLog]: List of SystemLog.
        """
        return (
            db.query(cls.model)
            .filter(cls.model.user_id == user_id)
            .order_by(cls.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def get_accuracy_logs(
        cls,
        db: Session,
        mode: str | None = None,
        accuracy_type: str | None = None,
        user_id: str | None = None,
        limit: int = 500,
    ) -> list[SystemLog]:
        """Retrieve accuracy logs.
        
        Args:
            db (Session): Database session.
            mode (str | None): The mode.
            accuracy_type (str | None): The accuracy type.
            user_id (str | None): Unique identifier of the user.
            limit (int): Limit integer.
        
        Returns:
            list[SystemLog]: List of SystemLog.
        """
        query = db.query(cls.model).filter(cls.model.label == "accuracy")
        if mode:
            query = query.filter(
                cls.model.metadata_json["mode"].as_string() == mode)
        if accuracy_type:
            query = query.filter(
                cls.model.metadata_json["accuracy_type"].as_string(
                ) == accuracy_type
            )
        if user_id:
            query = query.filter(cls.model.user_id == user_id)
        return (
            query.order_by(cls.model.created_at.desc())
            .limit(limit)
            .all()
        )
