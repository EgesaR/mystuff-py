"""api/routes/files.py

File and folder management endpoints.
Pattern: router validates HTTP contract → delegates all logic to service layer.
"""

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import NotificationType
from app.models.user import User
from app.schemas.file import FileResponse
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate
from app.services.file_service import FileService
from app.services.folder_service import FolderService
from app.services.notification_service import NotificationService

logger = logging.getLogger("app")
router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# FOLDERS
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/folders",
    response_model=list[FolderResponse],
    summary="List folders (root or children of a parent)",
)
def list_folders(
    parent_id: str | None = Query(
        None, description="Parent folder ID. Omit for root folders."
    ),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[FolderResponse]:
    """List folders.
    
    Args:
        parent_id (str | None): Unique identifier of the target resource.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        list[FolderResponse]: List of FolderResponse.
    """
    return FolderService.list_folders(
        db, user_id=current_user.id, parent_id=parent_id
    )


@router.post(
    "/folders",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a folder",
)
def create_folder(
    payload: FolderCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> FolderResponse:
    """Create folder.
    
    Args:
        payload (FolderCreate): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        FolderResponse: FolderResponse payload.
    """
    try:
        return FolderService.create_folder(
            db,
            user_id=current_user.id,
            name=payload.name,
            color=payload.color,
            parent_id=payload.parent_id,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent folder not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/folders/{folder_id}",
    response_model=FolderResponse,
    summary="Rename or recolor a folder",
)
def update_folder(
    folder_id: str,
    payload: FolderUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> FolderResponse:
    """Update folder.
    
    Args:
        folder_id (str): Unique identifier of the folder.
        payload (FolderUpdate): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        FolderResponse: FolderResponse payload.
    """
    try:
        return FolderService.update_folder(
            db,
            folder_id=folder_id,
            user_id=current_user.id,
            data=payload.model_dump(exclude_unset=True),
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.delete(
    "/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a folder (cascades to children)",
)
def delete_folder(
    folder_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete folder.
    
    Args:
        folder_id (str): Unique identifier of the folder.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        None: None result.
    """
    try:
        FolderService.delete_folder(
            db, folder_id=folder_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.get(
    "/folders/{folder_id}/tree",
    response_model=FolderResponse,
    summary="Get a folder with its full nested children tree",
)
def folder_tree(
    folder_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> FolderResponse:
    """Folder tree.
    
    Args:
        folder_id (str): Unique identifier of the folder.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        FolderResponse: FolderResponse payload.
    """
    try:
        return FolderService.get_folder_tree(
            db, folder_id=folder_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


# ══════════════════════════════════════════════════════════════════════════════
# FILES
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "",
    response_model=list[FileResponse],
    summary="List files (optionally filtered by folder)",
)
def list_files(
    folder_id: str | None = Query(None),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[FileResponse]:
    """List files.
    
    Args:
        folder_id (str | None): Unique identifier of the folder.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        list[FileResponse]: List of FileResponse.
    """
    return FileService.list_files(
        db, user_id=current_user.id, folder_id=folder_id
    )


@router.post(
    "/upload",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file (optionally into a folder)",
)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: str | None = Form(None),
    name: str | None = Form(None),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Upload file.
    
    Args:
        background_tasks (BackgroundTasks): The background tasks.
        file (UploadFile): The file.
        folder_id (str | None): Unique identifier of the folder.
        name (str | None): The name.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        FileResponse: FileResponse payload.
    """
    try:
        created = await FileService.upload_file(
            db,
            upload=file,
            owner=current_user,
            folder_id=folder_id,
            display_name=name,
        )

        NotificationService.create(
            db=db,
            recipient_id=current_user.id,
            title="Upload complete",
            message=f"{created.name} finished uploading.",
            notification_type=NotificationType.INFO,
            background_tasks=background_tasks,
        )

        return created

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        ) from exc

    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
