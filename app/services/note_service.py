"""Note service module managing business logic operations for notes."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.note import Note
from app.repositories.note_repository import NoteRepository


class NoteService:
    """Service class encapsulating application logic for Note management."""

    @staticmethod
    def list_notes(
        db: Session, user_id: str, folder_id: str | None = None
    ) -> list[Note]:
        """List notes for a user, optionally filtering by folder structure."""
        return NoteRepository.get_user_notes(db, user_id, folder_id)

    @staticmethod
    def list_pinned(db: Session, user_id: str) -> list[Note]:
        """List all pinned notes for a specific user identity."""
        return NoteRepository.get_pinned_notes(db, user_id)

    @staticmethod
    def search_notes(db: Session, user_id: str, query: str) -> list[Note]:
        """Execute text query search across a user's notes collection."""
        return NoteRepository.search_notes(db, user_id, query)

    @staticmethod
    def create_note(
        db: Session,
        owner_id: str,
        title: str,
        content: dict[str, Any] | None,
        folder_id: str | None,
        color: str | None,
    ) -> Note:
        """Create and persist a new note record."""
        note_data = {
            "owner_id": owner_id,
            "title": title,
            "content": content,
            "folder_id": folder_id,
            "color": color,
        }
        # Fixed: Changed back to obj_in for the create method
        return NoteRepository.create(db, obj_in=note_data)

    @staticmethod
    def get_note(db: Session, note_id: str, user_id: str) -> Note:
        """Fetch a specific note and explicitly verify owner permissions."""
        note = NoteRepository.get(db, note_id)
        if not note:
            raise NotFoundError("Note not found")
        if note.owner_id != user_id:
            raise PermissionDeniedError("Access denied")
        return note

    @staticmethod
    def update_note(
        db: Session, note_id: str, user_id: str, data: dict[str, Any]
    ) -> Note:
        """Modify fields on an existing note record."""
        note = NoteService.get_note(db, note_id, user_id)
        return NoteRepository.update(db, db_obj=note, update_data=data)

    @staticmethod
    def set_pinned(
        db: Session, note_id: str, user_id: str, pinned: bool
    ) -> Note:
        """Toggle the pinning state of an authorized note."""
        note = NoteService.get_note(db, note_id, user_id)
        return NoteRepository.update(
            db, db_obj=note, update_data={"pinned": pinned}
        )

    @staticmethod
    def move_note(
        db: Session, note_id: str, user_id: str, folder_id: str | None
    ) -> Note:
        """Relocate an authorized note to a different folder target."""
        note = NoteService.get_note(db, note_id, user_id)
        return NoteRepository.update(
            db, db_obj=note, update_data={"folder_id": folder_id}
        )

    @staticmethod
    def delete_note(db: Session, note_id: str, user_id: str) -> None:
        """Permanently remove an authorized note record."""
        note = NoteService.get_note(db, note_id, user_id)
        # Fixed: Pass the fetched model instance as db_obj
        NoteRepository.delete(db, db_obj=note)
