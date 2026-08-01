"""app/api/routes/shares.py

Share endpoints — invite, list, and accept access grants for notes,
files, folders, and collections. Business logic lives in ShareService;
this router only handles HTTP contracts.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import ShareResourceType
from app.models.share import Share
from app.models.user import User
from app.schemas.share import ShareAcceptRequest, ShareCreate, ShareResponse
from app.services.share_service import ShareService

logger = logging.getLogger("app")
router = APIRouter()


@router.get(
    "/incoming",
    response_model=list[ShareResponse],
    summary="List share invites sent to the current user",
)
def list_incoming_shares(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Share]:
    """List incoming shares.

    Args:
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        list[Share]: List of Share.
    """
    return ShareService.list_incoming(db, current_user.id)


@router.get(
    "/for-resource/{resource_type}/{resource_id}",
    response_model=list[ShareResponse],
    summary="List shares the current user has issued for a resource",
)
def list_shares_for_resource(
    resource_type: ShareResourceType,
    resource_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Share]:
    """List shares for a resource.

    Args:
        resource_type (ShareResourceType): The resource type.
        resource_id (str): Unique identifier of the resource.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        list[Share]: List of Share.
    """
    return ShareService.list_for_resource(
        db, resource_type, resource_id, current_user.id
    )


@router.post(
    "",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite another user to a note, file, folder, or collection",
)
def create_share(
    payload: ShareCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Share:
    """Create a share invite.

    Args:
        payload (ShareCreate): Request payload.
        background_tasks (BackgroundTasks): The background tasks.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        Share: Share result.
    """
    try:
        return ShareService.create_share(
            db,
            owner_id=current_user.id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            target_username=payload.target_username,
            permission=payload.permission,
            background_tasks=background_tasks,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post(
    "/accept",
    response_model=ShareResponse,
    summary="Accept a share invite using its token",
)
def accept_share(
    payload: ShareAcceptRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Share:
    """Accept a share invite.

    Args:
        payload (ShareAcceptRequest): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        Share: Share result.
    """
    try:
        return ShareService.accept_share(
            db, token=payload.token, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
