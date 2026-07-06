"""Application-wide enumeration types."""

from enum import StrEnum


class MediaType(StrEnum):
    """Allowed media types for files."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    GIF = "gif"


class NoteMediaType(StrEnum):
    """Allowed media types specifically for notes."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    GIF = "gif"


class LogLevel(StrEnum):
    """Application logging levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class NotificationType(StrEnum):
    """Types of system notifications."""

    SYSTEM_ALERT = "system_alert"
    INVITE = "invite"
    PRODUCT_UPDATE = "product_update"
