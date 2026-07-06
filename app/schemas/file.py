"""Pydantic models for file representation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MediaType


class FileResponse(BaseModel):
    """Schema for file metadata and access details."""

    id: str

    name: str
    original_name: str

    file_path: str
    url: str

    mime_type: str | None

    size_bytes: int

    media_type: MediaType

    folder_id: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class FileUploadResponse(BaseModel):
    """Schema for the response after a successful file upload."""

    file: FileResponse
    message: str = "File uploaded successfully"
