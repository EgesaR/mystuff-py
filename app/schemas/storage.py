"""Data structures for storage and file upload operations."""

from typing import TypedDict

from app.models.enums import MediaType


class UploadResult(TypedDict):
    """Represents the result of a successful file upload operation."""

    file_path: str
    url: str
    mime_type: str
    size_bytes: int
    original_name: str
    unique_name: str
    media_type: MediaType
