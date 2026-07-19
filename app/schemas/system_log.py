"""Pydantic schemas for system logs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import LogLevel


class SystemLogResponse(BaseModel):
    """Schema for a single system log row."""

    id: str
    level: LogLevel
    label: str
    message: str
    source: str | None
    metadata_json: dict[str, Any] | None
    user_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
