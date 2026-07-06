"""Note repository module handling database queries for Note models."""

from sqlalchemy.orm import Session

from app.models.note import Note
from app.repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Repository class for executing database operations on Note records."""

    model: type[Note] = Note

    @classmethod
    def get_user_notes(
        cls,
        db: Session,
        user_id: str,
        folder_id: str | None = None,
    ) -> list[Note]:
        """Retrieve all notes belonging to a user, optionally filtered by folder."""
        query = db.query(cls.model).filter(cls.model.owner_id == user_id)
        if folder_id is not None:
            # Type annotation on cls.model above helps Pylint see the new attribute
            query = query.filter(cls.model.folder_id == folder_id)
        return query.all()

    @classmethod
    def get_pinned_notes(cls, db: Session, user_id: str) -> list[Note]:
        """Retrieve all pinned notes belonging to a specific user."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.owner_id == user_id,
                cls.model.pinned.is_(True),
            )
            .all()
        )

    @classmethod
    def search_notes(cls, db: Session, user_id: str, query: str) -> list[Note]:
        """Perform a case-insensitive search on note titles."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.owner_id == user_id,
                cls.model.title.ilike(f"%{query}%"),
            )
            .all()
        )
