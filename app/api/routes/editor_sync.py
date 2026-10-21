"""REST endpoints for server-encrypted editor snapshots."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.user import User
from app.schemas.editor_sync import EditorSnapshotPayload
from app.services.editor_sync_service import (
    EncryptionUnavailableError,
    LegacyNoteContentError,
    SnapshotConflictError,
    SnapshotIntegrityError,
    get_accessible_note,
    is_editor_snapshot,
    read_snapshot,
    save_snapshot,
)

logger = logging.getLogger("app")
router = APIRouter()


@router.get(
    "/{note_id}/editor-snapshot",
    summary="Get a decrypted editor snapshot",
)
def get_editor_snapshot(
    note_id: UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Read an editor snapshot if the user can view the note."""
    try:
        note = get_accessible_note(
            db,
            note_id=note_id,
            user_id=current_user.id,
        )
        snapshot = read_snapshot(note)
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

    if snapshot is None:
        return {
            "revision": 0,
            "document": None,
            "requiresMigration": (
                note.content is not None
                and note.content != {}
                and not is_editor_snapshot(note.content)
            ),
        }
    revision, document = snapshot
    return {"revision": revision, "document": document}


@router.put(
    "/{note_id}/editor-snapshot",
    summary="Create or update a server-encrypted editor snapshot",
)
def put_editor_snapshot(
    note_id: UUID,
    payload: EditorSnapshotPayload,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Persist a full editor snapshot with optimistic concurrency control."""
    try:
        revision, document = save_snapshot(
            db,
            note_id=note_id,
            user=current_user,
            payload=payload,
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
    except LegacyNoteContentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "note_requires_migration",
                "message": "Existing note content was not changed",
            },
        ) from exc
    except SnapshotConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "revision_conflict",
                "revision": exc.revision,
                "document": exc.document,
            },
        ) from exc
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
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"revision": revision, "document": document}
