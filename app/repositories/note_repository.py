"""Note repository handling database queries for Note models."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.note import Note
from app.repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Repository class for executing database operations on Note records."""

    model: type[Note] = Note

    @classmethod
    def get_user_notes(
        cls, db: Session, user_id: UUID, folder_id: UUID | None = None
    ) -> list[Note]:
        """Retrieve user notes.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            folder_id (str | None): Unique identifier of the folder.
        
        Returns:
            list[Note]: List of Note.
        """
        query = db.query(cls.model).filter(cls.model.owner_id == user_id)

        if folder_id:
            query = query.filter(cls.model.folder_id == folder_id)

        # Assuming your Note model has a created_at column
        return query.order_by(cls.model.created_at.desc()).all()

    @classmethod
    def get_editor_notes(
        cls,
        db: Session,
        user_id: UUID,
        *,
        folder_id: UUID | None = None,
        query_text: str | None = None,
        pinned_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Note]:
        """Return a paginated note index ordered by most recently edited."""
        query = db.query(cls.model).filter(cls.model.owner_id == user_id)
        if folder_id is not None:
            query = query.filter(cls.model.folder_id == folder_id)
        if query_text:
            query = query.filter(cls.model.title.ilike(f"%{query_text}%"))
        if pinned_only:
            query = query.filter(cls.model.pinned.is_(True))
        return (
            query.order_by(cls.model.updated_at.desc(), cls.model.id.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @classmethod
    def get_pinned_notes(cls, db: Session, user_id: UUID) -> list[Note]:
        """Retrieve pinned notes.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[Note]: List of Note.
        """
        return (
            db.query(cls.model)
            .filter(cls.model.owner_id == user_id, cls.model.pinned.is_(True))
            .order_by(cls.model.created_at.desc())
            .all()
        )

    @classmethod
    def search_notes(cls, db: Session, user_id: UUID, query: str) -> list[Note]:
        """Search notes.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            query (str): Query string.
        
        Returns:
            list[Note]: List of Note.
        """
        search_term = f"%{query}%"
        return (
            db.query(cls.model)
            .filter(
                cls.model.owner_id == user_id,
                cls.model.title.ilike(search_term)
            )
            .order_by(cls.model.created_at.desc())
            .all()
        )
