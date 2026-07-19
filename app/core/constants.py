"""Application-wide constants and configuration values."""

# ── Images ───────────────────────────────────────────────────────────────
# Common web/raster formats plus the phone-camera and design formats users
# actually upload (HEIC/HEIF from iPhones, SVG/ICO from design exports).
ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/svg+xml",
    "image/bmp",
    "image/x-ms-bmp",
    "image/tiff",
    "image/heic",
    "image/heif",
    "image/avif",
    "image/x-icon",
    "image/vnd.microsoft.icon",
}

# ── Video ────────────────────────────────────────────────────────────────
ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",  # .mov
    "video/x-msvideo",  # .avi
    "video/x-matroska",  # .mkv
    "video/mpeg",
    "video/3gpp",
    "video/3gpp2",
    "video/ogg",
    "video/x-flv",
}

# ── Audio ────────────────────────────────────────────────────────────────
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",  # .mp3
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/mp4",  # .m4a
    "audio/aac",
    "audio/flac",
    "audio/x-flac",
    "audio/opus",
    "audio/amr",
    "audio/3gpp",
}

# ── Documents ────────────────────────────────────────────────────────────
# Not audio/video/image, but still common "file manager" uploads — office
# docs, PDFs, and plain text/data formats.
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-powerpoint",  # .ppt
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.oasis.opendocument.text",  # .odt
    "application/vnd.oasis.opendocument.spreadsheet",  # .ods
    "application/vnd.oasis.opendocument.presentation",  # .odp
    "application/rtf",
    "text/plain",
    "text/csv",
    "text/markdown",
    "application/json",
}

# ── Archives ─────────────────────────────────────────────────────────────
ALLOWED_ARCHIVE_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/x-rar-compressed",
    "application/vnd.rar",
    "application/x-7z-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
}

# Union of everything the app will accept anywhere a generic "any file" drop
# is allowed (e.g. the Cloud Storage "Upload" panel, as opposed to the
# narrower image-only / audio-only endpoints).
ALL_ALLOWED_TYPES: set[str] = (
    ALLOWED_IMAGE_TYPES
    | ALLOWED_VIDEO_TYPES
    | ALLOWED_AUDIO_TYPES
    | ALLOWED_DOCUMENT_TYPES
    | ALLOWED_ARCHIVE_TYPES
)

MAX_IMAGE_SIZE_MB = 20
MAX_VIDEO_SIZE_MB = 500
MAX_AUDIO_SIZE_MB = 100
MAX_DOCUMENT_SIZE_MB = 50
MAX_ARCHIVE_SIZE_MB = 500
MAX_GENERIC_FILE_SIZE_MB = 500  # fallback cap for mime types outside the sets above

DEFAULT_FOLDER_COLOR = "#6366f1"
DEFAULT_NOTE_COLOR = "#ffffff"
DEFAULT_COLLECTION_COLOR = "#6366f1"


def is_allowed_mime(mime_type: str) -> bool:
    """Return whether `mime_type` is on any of the allow-lists above.

    Not wired into the upload path yet — StorageService.upload_file()
    currently accepts anything. Call this from FileService.upload_file()
    (or StorageService) if you want to start rejecting unknown types.
    """
    return mime_type in ALL_ALLOWED_TYPES


def max_size_mb_for(mime_type: str) -> int:
    """Return the size cap that applies to `mime_type`, falling back to
    MAX_GENERIC_FILE_SIZE_MB for anything not in a specific category.
    """
    if mime_type in ALLOWED_IMAGE_TYPES:
        return MAX_IMAGE_SIZE_MB
    if mime_type in ALLOWED_VIDEO_TYPES:
        return MAX_VIDEO_SIZE_MB
    if mime_type in ALLOWED_AUDIO_TYPES:
        return MAX_AUDIO_SIZE_MB
    if mime_type in ALLOWED_DOCUMENT_TYPES:
        return MAX_DOCUMENT_SIZE_MB
    if mime_type in ALLOWED_ARCHIVE_TYPES:
        return MAX_ARCHIVE_SIZE_MB
    return MAX_GENERIC_FILE_SIZE_MB
