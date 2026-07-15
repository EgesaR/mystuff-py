"""Module containing the operational log orchestration service."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.ai.nlp.accuracy import AccuracyResult, AccuracyType
from app.models.enums import LogLevel
from app.models.system_log import SystemLog
from app.repositories.log_repository import LogRepository

logger = logging.getLogger("app")

ACCURACY_LABEL = "accuracy"


class LogService:
    """Orchestrates database operations and tracking workflows for system logs."""

    @staticmethod
    def log(
        db: Session,
        user_id: str | None,
        message: str,
        level: LogLevel = LogLevel.INFO,
        label: str = "general",
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SystemLog:
        """Commit a structured system log entry to the tracking repository.

        NOTE: `label` previously wasn't being set here even though the
        column is non-nullable — any call to this without a DB-level
        default on `label` would have raised an IntegrityError. Giving it
        a "general" default fixes that without changing the call signature
        for existing callers.
        """
        log_entry = SystemLog(
            user_id=user_id,
            message=message,
            level=level,
            label=label,
            source=source,
            metadata_json=metadata,
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
    def log_accuracy(
        db: Session,
        user_id: str | None,
        mode: str,
        accuracy_type: AccuracyType | str,
        result: AccuracyResult,
        source: str | None = None,
    ) -> SystemLog:
        """Log a word-accuracy measurement for a speech/lyrics transcript.

        `accuracy_type` is `AccuracyType.RAW_VS_PROCESSED` (reference-free,
        computed automatically for every finalised transcript) or
        `AccuracyType.PROCESSED_VS_CORRECTED` (computed only when the user
        submits a manual correction — the real ground-truth signal).
        """
        accuracy_type_value = (
            accuracy_type.value
            if isinstance(accuracy_type, AccuracyType)
            else accuracy_type
        )
        message = (
            f"{mode} [{accuracy_type_value}] word accuracy "
            f"{result.word_accuracy:.1%} (WER {result.word_error_rate:.1%}, "
            f"{result.reference_words} ref words)"
        )
        return LogService.log(
            db,
            user_id=user_id,
            message=message,
            level=LogLevel.INFO,
            label=ACCURACY_LABEL,
            source=source,
            metadata={
                "mode": mode,
                "accuracy_type": accuracy_type_value,
                **result.as_dict(),
            },
        )

    @staticmethod
    def get_accuracy_stats(
        db: Session,
        mode: str | None = None,
        accuracy_type: AccuracyType | str | None = None,
        user_id: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Aggregate word-accuracy logs: overall average plus a recent trend.

        `limit` bounds how many recent accuracy log rows are pulled before
        aggregating in Python — cheap and portable across SQLite/Postgres,
        and plenty for a trend view (raise it if you need deeper history).
        """
        accuracy_type_value = (
            accuracy_type.value
            if isinstance(accuracy_type, AccuracyType)
            else accuracy_type
        )
        logs = LogRepository.get_accuracy_logs(
            db,
            mode=mode,
            accuracy_type=accuracy_type_value,
            user_id=user_id,
            limit=limit,
        )

        if not logs:
            return {
                "count": 0,
                "average_word_accuracy": None,
                "average_word_error_rate": None,
                "recent_average_word_accuracy": None,
                "by_mode": {},
            }

        scores = [
            log.metadata_json["word_accuracy"]
            for log in logs
            if log.metadata_json and "word_accuracy" in log.metadata_json
        ]
        wers = [
            log.metadata_json["word_error_rate"]
            for log in logs
            if log.metadata_json and "word_error_rate" in log.metadata_json
        ]
        recent = scores[:20]  # logs come back newest-first

        by_mode: dict[str, dict[str, float | int]] = {}
        for log in logs:
            meta = log.metadata_json or {}
            log_mode = meta.get("mode", "unknown")
            if "word_accuracy" not in meta:
                continue
            bucket = by_mode.setdefault(log_mode, {"count": 0, "total": 0.0})
            bucket["count"] += 1
            bucket["total"] += meta["word_accuracy"]
        by_mode_summary = {
            mode_key: {
                "count": bucket["count"],
                "average_word_accuracy": round(bucket["total"] / bucket["count"], 4),
            }
            for mode_key, bucket in by_mode.items()
        }

        return {
            "count": len(logs),
            "average_word_accuracy": (
                round(sum(scores) / len(scores), 4) if scores else None
            ),
            "average_word_error_rate": (
                round(sum(wers) / len(wers), 4) if wers else None
            ),
            "recent_average_word_accuracy": (
                round(sum(recent) / len(recent), 4) if recent else None
            ),
            "by_mode": by_mode_summary,
        }

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
