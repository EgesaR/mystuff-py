"""Schemas for synchronized editor snapshots."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import JsonValue


class EditorSnapshotPayload(BaseModel):
    """A full editor document and the server revision it was based on."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    base_revision: int = Field(alias="baseRevision", ge=0, strict=True)
    document: dict[str, JsonValue]
    op_id: str | None = Field(default=None, alias="opId", max_length=64)
