"""Repository for note comment persistence and querying"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.comment import NoteComment
from app.repositories.base_repository import BaseRepository


class CommentRepository(BaseRepository[NoteComment]):
    """CRUD and note-scoped queries for NoteComment."""

    model = NoteComment

    @classmethod
    def get_for_note(cls, db: Session, note_id: UUID) -> list[NoteComment]:
        """List comments for a note, oldest first."""
        return (
            db.query(cls.model)
            .filter(cls.model.note_id == note_id)
            .order_by(cls.model.created_at.asc())
            .all()
        )
