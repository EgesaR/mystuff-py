from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

TabGroupColor = Literal["slate", "sage", "teal", "blue", "violet", "rose", "amber"]


class WorkspaceTabPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    doc_id: str = Field(alias="docId", min_length=1, max_length=128)
    label: str = Field(max_length=255)
    pinned: bool = False
    group_id: str | None = Field(default=None, alias="groupId")
    is_preview: bool = Field(default=False, alias="isPreview")
    last_activated_at: int | None = Field(default=None, alias="lastActivatedAt", ge=0)
    created_at: int | None = Field(default=None, alias="createdAt", ge=0)
    updated_at: int | None = Field(default=None, alias="updatedAt", ge=0)


class WorkspaceGroupPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    color: TabGroupColor
    collapsed: bool = False
    created_at: int = Field(alias="createdAt", ge=0)
    updated_at: int = Field(alias="updatedAt", ge=0)


class ClosedTabPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tab: WorkspaceTabPayload
    group_id: str | None = Field(default=None, alias="groupId")
    index: int = Field(ge=0)
    closed_at: int = Field(alias="closedAt", ge=0)


class WorkspaceStatePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tabs: list[WorkspaceTabPayload] = Field(default_factory=list[WorkspaceTabPayload], max_length=100)
    groups: list[WorkspaceGroupPayload] = Field(default_factory=list[WorkspaceGroupPayload], max_length=30)
    closed_tabs: list[ClosedTabPayload] = Field(
        default_factory=list[ClosedTabPayload],
        alias="closedTabs",
        max_length=50,
    )
    active_tab_id: str | None = Field(
        default=None,
        alias="activeTabId",
        max_length=128,
    )
    # This is the local Zustand revision, not a server concurrency token.
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_references(self) -> "WorkspaceStatePayload":
        tab_ids = [tab.id for tab in self.tabs]
        group_ids = [group.id for group in self.groups]

        if len(tab_ids) != len(set(tab_ids)):
            raise ValueError("Workspace contains duplicate tab IDs")
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("Workspace contains duplicate group IDs")

        known_groups = set(group_ids)
        for tab in self.tabs:
            if tab.group_id is not None and tab.group_id not in known_groups:
                raise ValueError(f"Tab {tab.id} references an unknown group")

        if self.active_tab_id is not None and self.active_tab_id not in set(tab_ids):
            raise ValueError("activeTabId must reference an existing tab")

        return self
