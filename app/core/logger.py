"""Centralized logging configuration."""

from logging import getLogger
from logging.config import dictConfig


def setup_logging() -> None:
    """Initialize the application logging configuration."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": (
                        "%(asctime)s | "
                        "%(levelname)s | "
                        "%(name)s | "
                        "%(message)s"
                    ),
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": "INFO",
            },
        }
    )


logger = getLogger("app")
