"""Pydantic schemas for collections."""

from datetime import datetime

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    color: str = Field(default="#6366f1", max_length=20)


class CollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    color: str | None = Field(default=None, max_length=20)


class CollectionResponse(BaseModel):
    id: str
    name: str
    color: str
    owner_id: str
    file_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectionFileAdd(BaseModel):
    file_id: str
