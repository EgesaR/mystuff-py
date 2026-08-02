"""Module containing logic and services for media items."""

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.enums import MediaType, NoteMediaType
from app.models.media import AudioNote, MediaItem, NoteMedia
from app.repositories.media_repository import (
    AudioNoteRepository,
    MediaItemRepository,
    NoteMediaRepository,
)
from app.services.note_service import NoteService
from app.services.storage_service import StorageService


class MediaService:
    """Orchestrates workflows for audio files and visual gallery items."""

    @staticmethod
    def list_audio_notes(db: Session, user_id: str) -> list[AudioNote]:
        """List audio notes."""
        return AudioNoteRepository.get_user_audio_notes(db, user_id=user_id)

    @staticmethod
    def upload_audio_note(
        db: Session,
        upload: UploadFile,
        owner_id: str,
        title: str,
        duration_sec: float | None = None,
    ) -> AudioNote:
        """Upload audio note."""
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
        """Retrieve audio note."""
        return AudioNoteRepository.get_secure_by_id(
            db, entity_id=note_id, user_id=user_id
        )

    @staticmethod
    def delete_audio_note(db: Session, note_id: str, user_id: str) -> None:
        """Delete audio note."""
        audio_note = AudioNoteRepository.get_secure_by_id(
            db, entity_id=note_id, user_id=user_id
        )
        AudioNoteRepository.delete(db, db_obj=audio_note)

    @staticmethod
    def list_gallery(
        db: Session, user_id: str, media_type: MediaType | None = None
    ) -> list[MediaItem]:
        """List gallery."""
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
        """Upload gallery item."""
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
        """Retrieve gallery item."""
        return MediaItemRepository.get_secure_by_id(
            db, entity_id=item_id, user_id=user_id
        )

    @staticmethod
    def delete_gallery_item(db: Session, item_id: str, user_id: str) -> None:
        """Delete gallery item."""
        media_item = MediaItemRepository.get_secure_by_id(
            db, entity_id=item_id, user_id=user_id
        )
        MediaItemRepository.delete(db, db_obj=media_item)

    @staticmethod
    async def add_note_image(
        db: Session, note_id: str, upload: UploadFile, user_id: str
    ) -> NoteMedia:
        """Upload an image and attach it to a note's media list.

        Scoped to images only, matching the editor's "Insert image" action.
        Requires ownership or an EDIT share on the note.
        """
        NoteService.require_edit_access(db, note_id, user_id)

        if not upload.content_type or not upload.content_type.startswith("image/"):
            raise ValueError("Only image files are allowed.")

        stored = await StorageService.upload_file(file=upload, owner_id=user_id)

        return NoteMediaRepository.create(
            db,
            obj_in={
                "note_id": note_id,
                "url": stored["url"],
                "media_type": NoteMediaType.IMAGE,
                "caption": None,
            },
        )

    @staticmethod
    def attach_media_to_note(
        db: Session, note_id: str, media_item_id: str, user_id: str
    ) -> NoteMedia:
        """Attach an existing gallery MediaItem to a note as a NoteMedia entry.

        NoteMedia has no foreign key to MediaItem; it stores its own
        url/media_type/caption, so this copies those across.
        """
        NoteService.require_edit_access(db, note_id, user_id)
        media_item = MediaItemRepository.get_secure_by_id(
            db, entity_id=media_item_id, user_id=user_id
        )

        return NoteMediaRepository.create(
            db,
            obj_in={
                "note_id": note_id,
                "url": media_item.url,
                "media_type": media_item.media_type,
                "caption": media_item.title,
            },
        )
