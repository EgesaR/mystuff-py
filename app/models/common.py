"""Common Pydantic schemas used across the application."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TimestampSchema(BaseModel):
    """Schema for models that include timestamp tracking."""

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class MessageResponse(BaseModel):
    """Standard schema for simple message responses."""

    message: str


class PaginationParams(BaseModel):
    """Schema for defining pagination request parameters."""

    page: int = 1
    per_page: int = 20


class PaginatedResponse(BaseModel):
    """Schema for standardized paginated API responses."""

    total: int
    page: int
    per_page: int
