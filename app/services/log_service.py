"""Module containing the operational log orchestration service."""

import logging

from sqlalchemy.orm import Session

from app.models.enums import LogLevel
from app.models.system_log import SystemLog

logger = logging.getLogger("app")


class LogService:
    """Orchestrates database operations and tracking workflows for system logs."""

    @staticmethod
    def log(
        db: Session,
        user_id: str | None,
        message: str,
        level: LogLevel = LogLevel.INFO,
    ) -> SystemLog:
        """Commit a structured system log entry to the tracking repository."""
        log_entry = SystemLog(
            user_id=user_id,
            message=message,
            level=level,
        )

        try:
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)

            logger.info("[%s] %s", level, message)
            return log_entry

        except Exception:
            db.rollback()
            logger.exception("Failed to write system log")
            raise

    @staticmethod
    def search(
        db: Session,
        user_id: str | None = None,
        regex_pattern: str | None = None,
        limit: int = 100,
    ) -> list[SystemLog]:
        """Filter and search stored logs using standard matching operations."""
        query = db.query(SystemLog)
        if user_id:
            query = query.filter(SystemLog.user_id == user_id)
        if regex_pattern:
            query = query.filter(SystemLog.message.op("~")(regex_pattern))

        # Split across lines to sit comfortably under Ruff's 88-char limit
        return (
            query.order_by(SystemLog.id.desc())
            .limit(limit)
            .all()
        )
