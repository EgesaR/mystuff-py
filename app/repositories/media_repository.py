"""Database abstraction layers and query builders for media assets."""

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import MediaType
from app.models.media import AudioNote, MediaItem, NoteMedia
from app.repositories.base_repository import BaseRepository


class NoteMediaRepository(BaseRepository[NoteMedia]):
    """Implements repository abstraction patterns for linking items."""

    model = NoteMedia

    @classmethod
    def get_note_media(cls, db: Session, note_id: str) -> list[NoteMedia]:
        """Fetch all contextual media reference joins tracking to a note."""
        return (
            db.query(cls.model)
            .filter(cls.model.note_id == note_id)
            .all()
        )


class AudioNoteRepository(BaseRepository[AudioNote]):
    """Implements data engine abstractions for processing user voice docs."""

    model = AudioNote

    @classmethod
    def get_user_audio_notes(cls, db: Session, user_id: str) -> list[AudioNote]:
        """Fetch structural records matching user identification profiles."""
        return (
            db.query(cls.model)
            .filter(cls.model.owner_id == user_id)
            .all()
        )

    @classmethod
    def get_secure_by_id(
        cls, db: Session, entity_id: str, user_id: str
    ) -> AudioNote:
        """Retrieve target item checking multi-tenant security bounds."""
        item = db.query(cls.model).filter(cls.model.id == entity_id).first()
        if not item:
            raise NotFoundError("Audio note not found")
        if item.owner_id != user_id:
            raise PermissionDeniedError("Access denied")
        return item


class MediaItemRepository(BaseRepository[MediaItem]):
    """Manages state transitions for structural gallery records."""

    model = MediaItem

    @classmethod
    def get_user_media(cls, db: Session, user_id: str) -> list[MediaItem]:
        """Query complete collection lists bounded to the explicit owner."""
        return (
            db.query(cls.model)
            .filter(cls.model.owner_id == user_id)
            .all()
        )

    @classmethod
    def get_filtered_media(
        cls, db: Session, user_id: str, media_type: MediaType | None = None
    ) -> list[MediaItem]:
        """Build a tracking block filtered by asset media groupings."""
        query = db.query(cls.model).filter(cls.model.owner_id == user_id)
        if media_type:
            query = query.filter(cls.model.media_type == media_type)
        return query.all()

    @classmethod
    def get_secure_by_id(
        cls, db: Session, entity_id: str, user_id: str
    ) -> MediaItem:
        """Assert entity allocation bounds before output validation steps."""
        item = db.query(cls.model).filter(cls.model.id == entity_id).first()
        if not item:
            raise NotFoundError("Media item not found")
        if item.owner_id != user_id:
            raise PermissionDeniedError("Access denied")
        return item
