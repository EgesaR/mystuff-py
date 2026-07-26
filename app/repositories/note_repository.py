"""Note repository handling database queries for Note models."""

from sqlalchemy.orm import Session

from app.models.note import Note
from app.repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Repository class for executing database operations on Note records."""

    model: type[Note] = Note

    @classmethod
    def get_user_notes(
        cls, db: Session, user_id: str, folder_id: str | None = None
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
    def get_pinned_notes(cls, db: Session, user_id: str) -> list[Note]:
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
    def search_notes(cls, db: Session, user_id: str, query: str) -> list[Note]:
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
