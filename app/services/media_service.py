"""Module containing logic and services for media items."""

from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.enums import MediaType
from app.models.media import AudioNote, MediaItem
from app.repositories.media_repository import (
    AudioNoteRepository,
    MediaItemRepository,
)


class MediaService:
    """Orchestrates workflows for audio files and visual gallery items."""

    @staticmethod
    def list_audio_notes(db: Session, user_id: str) -> list[AudioNote]:
        """List audio notes.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[AudioNote]: List of AudioNote.
        """
        return AudioNoteRepository.get_user_audio_notes(db, user_id=user_id)

    @staticmethod
    def upload_audio_note(
        db: Session,
        upload: UploadFile,
        owner_id: str,
        title: str,
        duration_sec: float | None = None,
    ) -> AudioNote:
        """Upload audio note.
        
        Args:
            db (Session): Database session.
            upload (UploadFile): The upload.
            owner_id (str): Unique identifier of the target resource.
            title (str): Title string.
            duration_sec (float | None): The duration sec.
        
        Returns:
            AudioNote: AudioNote result.
        """
        mock_url = f"https://storage.local/audio/{upload.filename}"

        audio_data = {
            "owner_id": owner_id,
            "title": title,
            "url": mock_url,
            "duration_sec": duration_sec,
        }
        return AudioNoteRepository.create(db, obj_in=audio_data)

    @staticmethod
    def get_audio_note(db: Session, note_id: str, user_id: str) -> AudioNote:
        """Retrieve audio note.
        
        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.
        
        Returns:
            AudioNote: AudioNote result.
        """
        return AudioNoteRepository.get_secure_by_id(
            db, entity_id=note_id, user_id=user_id
        )

    @staticmethod
    def delete_audio_note(db: Session, note_id: str, user_id: str) -> None:
        """Delete audio note.
        
        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.
        
        Returns:
            None: None result.
        """
        audio_note = AudioNoteRepository.get_secure_by_id(
            db, entity_id=note_id, user_id=user_id
        )
        # Fixed: Pass the model instance to db_obj
        AudioNoteRepository.delete(db, db_obj=audio_note)

    @staticmethod
    def list_gallery(
        db: Session, user_id: str, media_type: MediaType | None = None
    ) -> list[MediaItem]:
        """List gallery.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            media_type (MediaType | None): The media type.
        
        Returns:
            list[MediaItem]: List of MediaItem.
        """
        return MediaItemRepository.get_filtered_media(
            db, user_id=user_id, media_type=media_type
        )

    @staticmethod
    def upload_gallery_item(
        db: Session,
        upload: UploadFile,
        owner_id: str,
        title: str | None = None,
    ) -> MediaItem:
        """Upload gallery item.
        
        Args:
            db (Session): Database session.
            upload (UploadFile): The upload.
            owner_id (str): Unique identifier of the target resource.
            title (str | None): The title.
        
        Returns:
            MediaItem: MediaItem result.
        """
        mock_url = f"https://storage.local/gallery/{upload.filename}"

        content_type = upload.content_type or ""
        if "gif" in content_type:
            inferred_type = MediaType.GIF
        elif "video" in content_type:
            inferred_type = MediaType.VIDEO
        else:
            inferred_type = MediaType.IMAGE

        item_data = {
            "owner_id": owner_id,
            "title": title or upload.filename or "Untitled",
            "url": mock_url,
            "media_type": inferred_type,
        }
        return MediaItemRepository.create(db, obj_in=item_data)

    @staticmethod
    def get_gallery_item(db: Session, item_id: str, user_id: str) -> MediaItem:
        """Retrieve gallery item.
        
        Args:
            db (Session): Database session.
            item_id (str): Unique identifier of the target resource.
            user_id (str): Unique identifier of the user.
        
        Returns:
            MediaItem: MediaItem result.
        """
        return MediaItemRepository.get_secure_by_id(
            db, entity_id=item_id, user_id=user_id
        )

    @staticmethod
    def delete_gallery_item(db: Session, item_id: str, user_id: str) -> None:
        """Delete gallery item.
        
        Args:
            db (Session): Database session.
            item_id (str): Unique identifier of the target resource.
            user_id (str): Unique identifier of the user.
        
        Returns:
            None: None result.
        """
        media_item = MediaItemRepository.get_secure_by_id(
            db, entity_id=item_id, user_id=user_id
        )
        # Fixed: Pass the model instance to db_obj
        MediaItemRepository.delete(db, db_obj=media_item)

    @staticmethod
    def attach_media_to_note(db: Session, note_id: str, media_id: str) -> Any:
        """Attach media to note.
        
        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            media_id (str): Unique identifier of the target resource.
        
        Returns:
            Any: Result value.
        """
        from app.repositories.note_repository import NoteRepository

        return NoteRepository.create(
            db,
            obj_in={
                "note_id": note_id,
                "media_id": media_id,
            },
        )
