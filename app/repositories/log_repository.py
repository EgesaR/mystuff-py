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

    @classmethod
    def get_accuracy_logs(
        cls,
        db: Session,
        mode: str | None = None,
        accuracy_type: str | None = None,
        user_id: str | None = None,
        limit: int = 500,
    ) -> list[SystemLog]:
        """Retrieve word-accuracy log entries (label="accuracy"), newest first.

        Filters on `mode`/`accuracy_type` use SQLite/Postgres JSON operators
        against `metadata_json`, so this stays a single query rather than
        pulling everything and filtering in Python.
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
