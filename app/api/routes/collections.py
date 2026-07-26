"""app/api/routes/collections.py

Collection endpoints — cross-folder groupings of files. Mount this router
in your API aggregator the same way notes/notifications are mounted, e.g.:

    app.include_router(
        collections.router, prefix="/api/files/collections", tags=["collections"]
    )

That prefix is what the Cloud Storage frontend assumes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.collection import (
    CollectionCreate,
    CollectionFileAdd,
    CollectionResponse,
    CollectionUpdate,
)
from app.schemas.file import FileResponse
from app.services.collection_service import CollectionService

logger = logging.getLogger("app")
router = APIRouter()


@router.get(
    "",
    response_model=list[CollectionResponse],
    summary="List the current user's collections",
)
def list_collections(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[CollectionResponse]:
    """List collections.
    
    Args:
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        list[CollectionResponse]: List of CollectionResponse.
    """
    return CollectionService.list_collections(db, user_id=current_user.id)


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
)
def create_collection(
    payload: CollectionCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> CollectionResponse:
    """Create collection.
    
    Args:
        payload (CollectionCreate): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        CollectionResponse: CollectionResponse payload.
    """
    collection = CollectionService.create_collection(
        db, user_id=current_user.id, name=payload.name, color=payload.color
    )
    return CollectionService.to_response(db, collection)


@router.patch(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Rename or recolor a collection",
)
def update_collection(
    collection_id: str,
    payload: CollectionUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> CollectionResponse:
    """Update collection.
    
    Args:
        collection_id (str): Unique identifier of the collection.
        payload (CollectionUpdate): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        CollectionResponse: CollectionResponse payload.
    """
    try:
        collection = CollectionService.update_collection(
            db,
            collection_id=collection_id,
            user_id=current_user.id,
            data=payload.model_dump(exclude_unset=True),
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
        ) from exc
    return CollectionService.to_response(db, collection)


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection (files are not deleted)",
)
def delete_collection(
    collection_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete collection.
    
    Args:
        collection_id (str): Unique identifier of the collection.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        None: None result.
    """
    try:
        CollectionService.delete_collection(
            db, collection_id=collection_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
        ) from exc


@router.get(
    "/for-file/{file_id}",
    response_model=list[CollectionResponse],
    summary="List collections a given file belongs to",
)
def list_file_collections(
    file_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[CollectionResponse]:
    """List file collections.
    
    Args:
        file_id (str): Unique identifier of the file.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        list[CollectionResponse]: List of CollectionResponse.
    """
    collections = CollectionService.get_file_collections(
        db, file_id=file_id, user_id=current_user.id
    )
    return [CollectionService.to_response(db, c) for c in collections]


@router.get(
    "/{collection_id}/files",
    response_model=list[FileResponse],
    summary="List files in a collection",
)
def list_collection_files(
    collection_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[FileResponse]:
    """List collection files.
    
    Args:
        collection_id (str): Unique identifier of the collection.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        list[FileResponse]: List of FileResponse.
    """
    try:
        return CollectionService.list_files(
            db, collection_id=collection_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
        ) from exc


@router.post(
    "/{collection_id}/files",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add a file to a collection",
)
def add_file_to_collection(
    collection_id: str,
    payload: CollectionFileAdd,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Add file to collection.
    
    Args:
        collection_id (str): Unique identifier of the collection.
        payload (CollectionFileAdd): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        None: None result.
    """
    try:
        CollectionService.add_file(
            db,
            collection_id=collection_id,
            file_id=payload.file_id,
            user_id=current_user.id,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete(
    "/{collection_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a file from a collection",
)
def remove_file_from_collection(
    collection_id: str,
    file_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove file from collection.
    
    Args:
        collection_id (str): Unique identifier of the collection.
        file_id (str): Unique identifier of the file.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.
    
    Returns:
        None: None result.
    """
    try:
        CollectionService.remove_file(
            db,
            collection_id=collection_id,
            file_id=file_id,
            user_id=current_user.id,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
        ) from exc
