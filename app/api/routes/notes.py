"""Note CRUD, filtered listing, editor index and media endpoints."""

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
from sqlalchemy.exc import IntegrityError
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
    SnapshotIntegrityError,
    is_editor_snapshot,
    snapshot_revision,
)
from app.services.media_service import MediaService
from app.services.note_service import NoteService

logger = logging.getLogger("app")

router = APIRouter()


# ---------------------------------------------------------------------------
# Response adapters
# ---------------------------------------------------------------------------


def _note_response(note: Note) -> NoteResponse:
    """Convert a SQLAlchemy note model into its API response."""
    return NoteResponse.model_validate(note)


def _editor_summary(note: Note) -> EditorNoteSummary:
    """Build lightweight editor metadata without decrypting the document."""
    try:
        revision = snapshot_revision(note)

    except SnapshotIntegrityError as exc:
        logger.exception(
            "Invalid editor snapshot metadata: note=%s",
            note.id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored editor snapshot is unavailable",
        ) from exc

    return EditorNoteSummary(
        id=str(note.id),
        title=note.title,
        createdAt=int(note.created_at.timestamp() * 1000),
        updatedAt=int(note.updated_at.timestamp() * 1000),
        revision=revision,
        hasEditorDocument=revision > 0,
        requiresMigration=(note.content not in (None, {}) and not is_editor_snapshot(note.content)),
        pinned=note.pinned,
        folderId=note.folder_id,
        color=note.color,
    )


# ---------------------------------------------------------------------------
# Note listing
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[NoteResponse],
    summary="List and search notes",
)
def list_notes(
    folder_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255),
    pinned_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[NoteResponse]:
    """List notes with optional folder, search and pin filters."""
    notes = NoteService.list_notes(
        db,
        current_user.id,
        folder_id=folder_id,
        query_text=q,
        pinned_only=pinned_only,
        limit=limit,
        offset=offset,
    )

    return [_note_response(note) for note in notes]


# ---------------------------------------------------------------------------
# Create note
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
)
def create_note(
    payload: NoteCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Create a note, optionally using a client-generated UUID."""
    try:
        note = NoteService.create_note(
            db,
            owner_id=current_user.id,
            note_id=payload.id,
            title=payload.title,
            content=payload.content,
            folder_id=payload.folder_id,
            color=payload.color,
        )

        return _note_response(note)

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        logger.warning(
            "Note creation conflict: user=%s note=%s",
            current_user.id,
            payload.id,
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A note with this ID already exists",
        ) from exc


# ---------------------------------------------------------------------------
# Editor index
# ---------------------------------------------------------------------------

# Keep these static routes above /{note_id}.
# The second path is retained as a hidden compatibility alias.


@router.get(
    "/editor-documents",
    response_model=list[EditorNoteSummary],
    include_in_schema=False,
)
@router.get(
    "/editor-index",
    response_model=list[EditorNoteSummary],
    summary="List lightweight editor note metadata",
)
def editor_index(
    folder_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255),
    pinned_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[EditorNoteSummary]:
    """Return paginated editor metadata without loading full documents."""
    notes = NoteService.list_editor_notes(
        db,
        current_user.id,
        folder_id=folder_id,
        query=q,
        pinned_only=pinned_only,
        limit=limit,
        offset=offset,
    )

    return [_editor_summary(note) for note in notes]


# ---------------------------------------------------------------------------
# Retrieve note
# ---------------------------------------------------------------------------


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Get a note",
)
def get_note(
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Retrieve a note accessible to the current user."""
    try:
        note = NoteService.get_note(
            db,
            note_id,
            current_user.id,
        )

        return _note_response(note)

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        ) from exc

    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        ) from exc


# ---------------------------------------------------------------------------
# Update note
# ---------------------------------------------------------------------------


@router.patch(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Update note metadata or legacy content",
)
def update_note(
    note_id: UUID,
    payload: NoteUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Update note metadata or legacy content.

    Encrypted editor documents must use the editor-snapshot endpoint
    for title and document changes.
    """
    try:
        note = NoteService.update_note(
            db,
            note_id=note_id,
            user_id=current_user.id,
            data=payload.model_dump(exclude_unset=True),
        )

        return _note_response(note)

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        ) from exc

    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit access required",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "use_editor_snapshot",
                "message": str(exc),
            },
        ) from exc


# ---------------------------------------------------------------------------
# Pin and unpin
# ---------------------------------------------------------------------------


@router.post(
    "/{note_id}/pin",
    response_model=NoteResponse,
    summary="Pin a note",
)
def pin_note(
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Pin a note."""
    return _set_note_pinned(
        db,
        note_id=note_id,
        user_id=current_user.id,
        pinned=True,
    )


@router.post(
    "/{note_id}/unpin",
    response_model=NoteResponse,
    summary="Unpin a note",
)
def unpin_note(
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Unpin a note."""
    return _set_note_pinned(
        db,
        note_id=note_id,
        user_id=current_user.id,
        pinned=False,
    )


def _set_note_pinned(
    db: Session,
    *,
    note_id: UUID,
    user_id: UUID,
    pinned: bool,
) -> NoteResponse:
    """Apply pin state and translate note access errors."""
    try:
        note = NoteService.set_pinned(
            db,
            note_id=note_id,
            user_id=user_id,
            pinned=pinned,
        )

        return _note_response(note)

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        ) from exc

    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit access required",
        ) from exc


# ---------------------------------------------------------------------------
# Move note
# ---------------------------------------------------------------------------

# Preserve the previous /move URL as a hidden compatibility alias.


@router.patch(
    "/{note_id}/move",
    response_model=NoteResponse,
    include_in_schema=False,
)
@router.patch(
    "/{note_id}/folder",
    response_model=NoteResponse,
    summary="Move a note to a folder or the root",
)
def move_note(
    note_id: UUID,
    folder_id: UUID | None = Query(default=None),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    """Move an owned note to a different folder or to the root."""
    try:
        note = NoteService.move_note(
            db,
            note_id=note_id,
            user_id=current_user.id,
            folder_id=folder_id,
        )

        return _note_response(note)

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note or folder not found",
        ) from exc

    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Delete note
# ---------------------------------------------------------------------------


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
    """Delete a note. Only its owner can perform this operation."""
    try:
        NoteService.delete_note(
            db,
            note_id,
            current_user.id,
        )

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        ) from exc

    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete a note",
        ) from exc


# ---------------------------------------------------------------------------
# Note media
# ---------------------------------------------------------------------------


@router.post(
    "/{note_id}/media",
    response_model=NoteMediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an image to a note",
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
            db,
            note_id=note_id,
            upload=file,
            user_id=current_user.id,
        )

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        ) from exc

    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit access required",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
