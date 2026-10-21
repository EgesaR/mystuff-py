"""Note CRUD + search + pin/unpin + media endpoints."""

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.media import NoteMedia
from app.models.note import Note
from app.models.user import User
from app.schemas.media import NoteMediaResponse
from app.schemas.note import (
    EditorNoteSummary,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)
from app.services.editor_sync_service import (
    EncryptionUnavailableError,
    SnapshotIntegrityError,
    is_editor_snapshot,
    read_snapshot,
)
from app.services.media_service import MediaService
from app.services.note_service import NoteService

logger = logging.getLogger("app")
router = APIRouter()


def _editor_note_summary(note: Note) -> EditorNoteSummary:
    """Adapt the persisted note row to the editor's camel-case document model."""
    try:
        snapshot = read_snapshot(note)
    except EncryptionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Note snapshot encryption is not configured",
        ) from exc
    except SnapshotIntegrityError as exc:
        logger.exception("Stored editor snapshot integrity check failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored editor snapshot is unavailable",
        ) from exc

    document = snapshot[1] if snapshot else None
    return EditorNoteSummary(
        id=str(note.id),
        title=note.title,
        createdAt=(
            int(document["createdAt"])
            if document and isinstance(document.get("createdAt"), (int, float))
            else int(note.created_at.timestamp() * 1000)
        ),
        updatedAt=(
            int(document["updatedAt"])
            if document and isinstance(document.get("updatedAt"), (int, float))
            else int(note.updated_at.timestamp() * 1000)
        ),
        revision=snapshot[0] if snapshot else 0,
        document=document,
        hasEditorDocument=snapshot is not None,
        requiresMigration=(
            note.content not in (None, {})
            and not is_editor_snapshot(note.content)
        ),
        pinned=note.pinned,
        folderId=note.folder_id,
        color=note.color,
    )


@router.get(
    "",
    response_model=list[NoteResponse],
    summary="List notes. Optionally filter by folder or search by text.",
)
def list_notes(
    folder_id: UUID | None = Query(None),
    q: str | None = Query(None, description="Full-text search query"),
    pinned_only: bool = Query(False),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Note]:
    """List notes for the current user."""
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
    """Create a new note."""
    try:
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
    "/editor-documents",
    response_model=list[EditorNoteSummary],
    summary="List notes in the editor document format",
)
def list_editor_documents(
    folder_id: UUID | None = Query(None),
    q: str | None = Query(None, max_length=255),
    pinned_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[EditorNoteSummary]:
    """List owned notes as browser-editor documents and migration metadata."""
    notes = NoteService.list_editor_notes(
        db,
        user_id=current_user.id,
        folder_id=folder_id,
        query=q,
        pinned_only=pinned_only,
        limit=limit,
        offset=offset,
    )
    return [_editor_note_summary(note) for note in notes]


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Get a single note",
)
def get_note(
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Retrieve a specific note."""
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
    note_id: UUID,
    payload: NoteUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Update an existing note."""
    try:
        if {"content", "title"} & payload.model_fields_set:
            existing = NoteService.get_note(
                db,
                note_id=note_id,
                user_id=current_user.id,
            )
            if is_editor_snapshot(existing.content):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Use the editor-snapshot endpoint to update this note",
                )
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
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Pin a note."""
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
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Unpin a note."""
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
    note_id: UUID,
    folder_id: UUID | None = Query(
        None, description="Target folder. Omit to move to root."
    ),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Note:
    """Move a note to a different folder."""
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
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a note."""
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


@router.post(
    "/{note_id}/media",
    response_model=NoteMediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image and attach it to this note",
)
async def upload_note_image(
    note_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NoteMedia:
    """Upload and attach an image to a note."""
    try:
        return await MediaService.add_note_image(
            db, note_id=note_id, upload=file, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
