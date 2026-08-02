"""app/api/routes/comments.py

Comment endpoints, nested under a note. Mount alongside your other
routers with the SAME prefix as notes.py:

    app.include_router(comments.router, prefix="/api/notes", tags=["comments"])
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.comment_service import CommentService

logger = logging.getLogger("app")
router = APIRouter()


@router.get(
    "/{note_id}/comments",
    response_model=list[CommentResponse],
    summary="List comments on a note",
)
def list_comments(
    note_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[CommentResponse]:
    try:
        return CommentService.list_comments(db, note_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Note not found") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Access denied") from exc


@router.post(
    "/{note_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a comment on a note",
)
def create_comment(
    note_id: str,
    payload: CommentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> CommentResponse:
    try:
        return CommentService.create_comment(
            db, note_id, current_user.id, payload.body, background_tasks
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Note not found") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Access denied") from exc


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment (author or note owner only)",
)
def delete_comment(
    comment_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        CommentService.delete_comment(db, comment_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Comment not found") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Access denied") from exc
