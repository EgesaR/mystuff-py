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

    # Your existing types
    SYSTEM_ALERT = "system_alert"
    INVITE = "invite"
    PRODUCT_UPDATE = "product_update"

    # New system status types
    INFO = "info"           # Fixes your crash!
    SUCCESS = "success"     # Perfect for "File uploaded successfully"
    WARNING = "warning"     # Perfect for "Storage space is almost full"
    ERROR = "error"         # Perfect for "File processing failed"

    # New social/collaboration types
    MENTION = "mention"         # When someone @tags a user
    NEW_MESSAGE = "new_message"  # Direct messages
    