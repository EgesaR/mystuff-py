"""Application-wide constants and configuration values."""

ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
}

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/wav",
    "audio/webm",
    "audio/ogg",
}

MAX_IMAGE_SIZE_MB = 20
MAX_VIDEO_SIZE_MB = 500
MAX_AUDIO_SIZE_MB = 100

DEFAULT_FOLDER_COLOR = "#6366f1"
DEFAULT_NOTE_COLOR = "#ffffff"
