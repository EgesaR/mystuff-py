"""Business logic for note comments, including @mention notifications"""

import re

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.comment import NoteComment
from app.models.enums import NotificationType
from app.repositories.comment_repository import CommentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentResponse
from app.services.note_service import NoteService
from app.services.notification_service import NotificationService

_MENTION_RE = re.compile(r"@(\w+)")


class CommentService:
    """Service layer for creating, listing, and deleting note comments."""

    @staticmethod
    def to_response(comment: NoteComment) -> CommentResponse:
        """Build a CommentResponse, resolving the author's username."""
        return CommentResponse(
            id=comment.id,
            note_id=comment.note_id,
            author_id=comment.author_id,
            author_username=comment.author.username,
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )

    @staticmethod
    def list_comments(
        db: Session,
        note_id: str,
        user_id: str
    ) -> list[CommentResponse]:
        """List comments for a note the user can access (owner or shared)."""
        NoteService.get_note(db, note_id, user_id)
        comments = CommentRepository.get_for_note(db, note_id)
        return [CommentService.to_response(c) for c in comments]


    @staticmethod
    def create_comment(
        db: Session,
        note_id: str,
        author_id: str,
        body: str,
        background_tasks: BackgroundTasks
    ) -> CommentResponse:
        """Post a comment. Notifies the note owner (if not the author) and any @mentioned users who have accounts."""
        note = NoteService.get_note(db, note_id, author_id)

        comment = CommentRepository.create(
            db, obj_in={"note_id": note_id, "author_id": author_id, "body": body}
        )

        notified: set[str] = {author_id}

        if note.owner_id not in notified:
            NotificationService.create(
                db=db,
                recipient_id=note.owner_id,
                sender_id=author_id,
                title="New comment on your note",
                message=body[:140],
                notification_type=NotificationType.COMMENT,
                link=f"/dashboard/notes/{note_id}",
                background_tasks=background_tasks
            )
            notified.add(note.owner_id)

        for username in set(_MENTION_RE.findall(body)):
            mentioned = UserRepository.get_by_username(db, username)
            if mentioned and mentioned.id not in notified:
                NotificationService.create(
                    db=db,
                    recipient_id=mentioned.id,
                    sender_id=author_id,
                    title="You were mentioned in a comment",
                    message=body[:140],
                    notification_type=NotificationType.MENTION,
                    link=f"/dashboard/notes/{note_id}",
                    background_tasks=background_tasks
                )
                notified.add(mentioned.id)

        return CommentService.to_response(comment)

    @staticmethod
    def delete_comment(db: Session, comment_id: str, user_id: str) -> None:
        """Delete a comment. Only its author or the note's owner may delete it."""
        comment = CommentRepository.get(db, comment_id)
        if not comment:
            raise NotFoundError("Comment not found")
        
        note = NoteService.get_note(db, comment.note_id, user_id)
        if comment.author_id != user_id and note.owner_id != user_id:
            raise PermissionDeniedError("Access denied")
        
        CommentRepository.delete(db, db_obj=comment)