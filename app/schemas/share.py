from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SharePermission, ShareResourceType, ShareStatus


class ShareCreate(BaseModel):
    resource_type: ShareResourceType
    resource_id: str
    target_username: str = Field(min_length=1)
    permission: SharePermission = SharePermission.VIEW


class ShareResponse(BaseModel):
    id: str
    resource_type: ShareResourceType
    resource_id: str
    owner_id: str
    target_user_id: str | None
    permission: SharePermission
    status: ShareStatus
    token: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShareAcceptRequest(BaseModel):
    token: str
