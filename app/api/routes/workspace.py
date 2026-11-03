"""Workspace tab and tab-group state endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.api.websocket.notifications import notification_manager
from app.models.user import User
from app.schemas.workspace import WorkspaceStatePayload
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ---------------------------------------------------------------------------
# Retrieve workspace
# ---------------------------------------------------------------------------


@router.get(
    "/sync",
    include_in_schema=False,
)
@router.get(
    "",
    summary="Get the current workspace",
)
def get_workspace(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, object] | None:
    """Retrieve the authenticated user's persisted workspace state."""
    return WorkspaceService.get_state(
        db,
        current_user.id,
    )


# ---------------------------------------------------------------------------
# Synchronize workspace
# ---------------------------------------------------------------------------


@router.post(
    "/sync",
    include_in_schema=False,
)
@router.put(
    "",
    summary="Save the current workspace",
)
def update_workspace(
    background_tasks: BackgroundTasks,
    payload: WorkspaceStatePayload,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Persist workspace state and notify connected user sessions."""
    result = WorkspaceService.sync_state(
        db,
        current_user.id,
        payload,
    )

    background_tasks.add_task(
        notification_manager.push,
        current_user.id,
        {
            "type": "WORKSPACE_UPDATED",
            "timestamp": result.get("updated_at"),
        },
    )

    return result
