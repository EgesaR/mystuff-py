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
        """Retrieve all logs of a specific severity level."""
        return db.query(cls.model).filter(cls.model.level == level).all()

    @classmethod
    def get_user_logs(
        cls, db: Session, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[SystemLog]:
        """Retrieve paginated logs associated with a specific user."""
        return (
            db.query(cls.model)
            .filter(cls.model.user_id == user_id)
            .order_by(cls.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
