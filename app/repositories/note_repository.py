"""Database queries for Note records."""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models.note import Note
from app.repositories.base_repository import BaseRepository


def _like_pattern(value: str) -> str:
    """Escape user-controlled SQL LIKE metacharacters."""
    escaped = value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class NoteRepository(BaseRepository[Note]):
    """Repository operations for note retrieval, listing and search."""

    model: type[Note] = Note

    @classmethod
    def get_user_notes(
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
        """Retrieve a user's notes with optional filtering and pagination.

        Args:
            db: Active database session.
            user_id: UUID of the note owner.
            folder_id: Optionally restrict results to a folder.
            query_text: Search term for note titles and plain text.
            pinned_only: Whether to return only pinned notes.
            limit: Maximum number of notes to return.
            offset: Number of matching notes to skip.

        Returns:
            Notes ordered by pinned status and most recent update.
        """
        query = db.query(cls.model).options(selectinload(cls.model.media)).filter(cls.model.owner_id == user_id)

        if folder_id is not None:
            query = query.filter(cls.model.folder_id == folder_id)

        if query_text and query_text.strip():
            pattern = _like_pattern(query_text)

            query = query.filter(
                or_(
                    cls.model.title.ilike(pattern, escape="\\"),
                    cls.model.plain_text.ilike(pattern, escape="\\"),
                )
            )

        if pinned_only:
            query = query.filter(cls.model.pinned.is_(True))

        return (
            query.order_by(
                cls.model.pinned.desc(),
                cls.model.updated_at.desc(),
                cls.model.id.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

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
        """Retrieve the editor's paginated note index.

        Shares filtering and ordering rules with the general note listing.
        """
        return cls.get_user_notes(
            db,
            user_id,
            folder_id=folder_id,
            query_text=query_text,
            pinned_only=pinned_only,
            limit=limit,
            offset=offset,
        )

    @classmethod
    def get_pinned_notes(
        cls,
        db: Session,
        user_id: UUID,
        *,
        limit: int = 100,
    ) -> list[Note]:
        """Retrieve pinned notes belonging to a user."""
        return cls.get_user_notes(
            db,
            user_id,
            pinned_only=True,
            limit=limit,
        )

    @classmethod
    def search_notes(
        cls,
        db: Session,
        user_id: UUID,
        query: str,
        *,
        limit: int = 100,
    ) -> list[Note]:
        """Search a user's notes by title and searchable plain text."""
        return cls.get_user_notes(
            db,
            user_id,
            query_text=query,
            limit=limit,
        )
