"""Workspace tab REST endpoints: fetch and sync state."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.api.websocket.notifications import notification_manager
from app.models.user import User
from app.services.workspace_service import WorkspaceService

router = APIRouter()


@router.get("/sync", summary="Get user workspace tab state")
def get_tab_state(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any] | None:
    """Retrieve tab state.
    
    Args:
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        dict[str, Any] | None: Response payload or None.
    """
    return WorkspaceService.get_state(db, current_user.id)


@router.post("/sync", summary="Sync user workspace tab state")
def sync_tab_state(
    background_tasks: BackgroundTasks,
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Sync tab state.
    
    Args:
        background_tasks (BackgroundTasks): The background tasks.
        payload (dict[str, Any]): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        dict[str, Any]: Response payload.
    """
    result = WorkspaceService.sync_state(db, current_user.id, payload)

    background_tasks.add_task(
        notification_manager.push,
        current_user.id,
        {
            "type": "WORKSPACE_UPDATED",
            "timestamp": result.get("updated_at")
        }

    )
    return result
