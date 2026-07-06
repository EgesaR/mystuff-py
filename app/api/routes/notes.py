"""Note CRUD + search + pin/unpin endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.services.note_service import NoteService

logger = logging.getLogger("app")
router = APIRouter()


@router.get(
    "",
    response_model=list[NoteResponse],
    summary="List notes. Optionally filter by folder or search by text.",
)
def list_notes(
    folder_id: str | None = Query(None),
    q: str | None = Query(None, description="Full-text search query"),
    pinned_only: bool = Query(False),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Note]:
    """Retrieve list of notes belonging to authenticated user with optional filters."""
    if q:
        return NoteService.search_notes(db, user_id=current_user.id, query=q)
    if pinned_only:
        return NoteService.list_pinned(db, user_id=current_user.id)
    return NoteService.list_notes(
        db, user_id=current_user.id, folder_id=folder_id
    )


@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note",
)
def create_note(
    payload: NoteCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Create and persist a new note record under the current authenticated user."""
    try:
        # With the NoteCreate schema updated, payload.folder_id is now valid
        return NoteService.create_note(
            db,
            owner_id=current_user.id,
            title=payload.title,
            content=payload.content,
            folder_id=payload.folder_id,
            color=payload.color,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        ) from exc

@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Get a single note",
)
def get_note(
    note_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Fetch details of a single note validated against user authorization scopes."""
    try:
        return NoteService.get_note(db, note_id=note_id, user_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.patch(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Update note content, title, color, or folder",
)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Partially modify properties of a specific authorized note instance."""
    try:
        return NoteService.update_note(
            db,
            note_id=note_id,
            user_id=current_user.id,
            data=payload.model_dump(exclude_unset=True),
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.post(
    "/{note_id}/pin",
    response_model=NoteResponse,
    summary="Pin a note",
)
def pin_note(
    note_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Set the pin metadata status of an active note to true."""
    try:
        return NoteService.set_pinned(
            db, note_id=note_id, user_id=current_user.id, pinned=True
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.post(
    "/{note_id}/unpin",
    response_model=NoteResponse,
    summary="Unpin a note",
)
def unpin_note(
    note_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Set the pin metadata status of an active note to false."""
    try:
        return NoteService.set_pinned(
            db, note_id=note_id, user_id=current_user.id, pinned=False
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.patch(
    "/{note_id}/move",
    response_model=NoteResponse,
    summary="Move note to a different folder (or root)",
)
def move_note(
    note_id: str,
    folder_id: str | None = Query(
        None, description="Target folder. Omit to move to root."
    ),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Relocate a target note into an alternate user directory or root structure."""
    try:
        return NoteService.move_note(
            db, note_id=note_id, user_id=current_user.id, folder_id=folder_id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note or folder not found",
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
)
def delete_note(
    note_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Permanently clear down and remove an authorized note entity from storage."""
    try:
        NoteService.delete_note(db, note_id=note_id, user_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc
