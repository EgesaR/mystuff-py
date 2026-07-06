"""api/routes/media.py
Media endpoints for handling voice notes and gallery files.
"""

import logging
from typing import Any

from fastapi import (
    APIRouter,
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
from app.models.enums import MediaType
from app.models.user import User
from app.schemas.media import AudioNoteResponse, MediaItemResponse
from app.services.media_service import MediaService

logger = logging.getLogger("app")

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO NOTES
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/audio",
    response_model=list[AudioNoteResponse],
    summary="List all audio notes for the current user",
)
def list_audio_notes(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Any]:
    """Retrieve all audio notes matching the context profile identifier."""
    return MediaService.list_audio_notes(db, user_id=current_user.id)


@router.post(
    "/audio",
    response_model=AudioNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new audio note",
)
async def upload_audio_note(
    file: UploadFile = File(...),
    title: str = Form("Voice Note"),
    duration_sec: float | None = Form(None),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Validate asset content typing and register incoming voice notes."""
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only audio files are allowed.",
        )

    try:
        # Fixed: Removed 'await' since service method is synchronous
        return MediaService.upload_audio_note(
            db,
            upload=file,
            owner_id=current_user.id,
            title=title,
            duration_sec=duration_sec,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "/audio/{note_id}",
    response_model=AudioNoteResponse,
    summary="Get a single audio note",
)
def get_audio_note(
    note_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Fetch an audio entity tracking reference by its unique token."""
    try:
        return MediaService.get_audio_note(
            db, note_id=note_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audio note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.delete(
    "/audio/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an audio note",
)
def delete_audio_note(
    note_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove target operational file structures and table assets."""
    try:
        MediaService.delete_audio_note(
            db, note_id=note_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audio note not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


# ══════════════════════════════════════════════════════════════════════════════
# MEDIA GALLERY  (images / videos / GIFs)
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/gallery",
    response_model=list[MediaItemResponse],
    summary="List gallery items (optionally filter by media type)",
)
def list_gallery(
    media_type: MediaType | None = Query(
        None, description="Filter: image | video | audio | gif"
    ),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Any]:
    """Retrieve indexed items stored across user visual asset structures."""
    return MediaService.list_gallery(
        db, user_id=current_user.id, media_type=media_type
    )


@router.post(
    "/gallery",
    response_model=MediaItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image, video, audio or GIF to the gallery",
)
async def upload_gallery_item(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Receive and index new incoming graphical or multi-format media."""
    try:
        # Fixed: Removed 'await' since service method is synchronous
        return MediaService.upload_gallery_item(
            db,
            upload=file,
            owner_id=current_user.id,
            title=title,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "/gallery/{item_id}",
    response_model=MediaItemResponse,
    summary="Get a single gallery item",
)
def get_gallery_item(
    item_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Look up item metadata definitions tied to structural file paths."""
    try:
        return MediaService.get_gallery_item(
            db, item_id=item_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc


@router.delete(
    "/gallery/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a gallery item",
)
def delete_gallery_item(
    item_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Purge targeted gallery structures safely across storage maps."""
    try:
        MediaService.delete_gallery_item(
            db, item_id=item_id, user_id=current_user.id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found"
        ) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        ) from exc
