"""Note service module managing business logic operations for notes."""

from typing import Any, cast

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
        """List notes for the current user.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            folder_id (str | None): Unique identifier of the folder.

        Returns:
            list[Note]: List of Note.
        """
        return NoteRepository.get_user_notes(db, user_id, folder_id)

    @staticmethod
    def list_pinned(db: Session, user_id: str) -> list[Note]:
        """List pinned.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.

        Returns:
            list[Note]: List of Note.
        """
        return NoteRepository.get_pinned_notes(db, user_id)

    @staticmethod
    def search_notes(db: Session, user_id: str, query: str) -> list[Note]:
        """Search notes.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            query (str): Query string.

        Returns:
            list[Note]: List of Note.
        """
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
        """Create a new note.

        Args:
            db (Session): Database session.
            owner_id (str): Unique identifier of the target resource.
            title (str): Title string.
            content (dict[str, Any] | None): The content.
            folder_id (str | None): Unique identifier of the folder.
            color (str | None): The color.

        Returns:
            Note: Note result.
        """
        note_data = {
            "owner_id": owner_id,
            "title": title,
            "content": content,
            "plain_text": (content or {}).get("text"),
            "folder_id": folder_id,
            "color": color,
        }
        # Fixed: Changed back to obj_in for the create method
        return NoteRepository.create(db, obj_in=note_data)

    @staticmethod
    def get_note(db: Session, note_id: str, user_id: str) -> Note:
        """Retrieve a specific note.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.

        Returns:
            Note: Note result.
        """
        note = NoteRepository.get(db, note_id)
        if not note:
            raise NotFoundError("Note not found")
        if note.owner_id != user_id:
            from app.models.enums import ShareResourceType
            from app.services.share_service import ShareService
            if not ShareService.has_access(db, ShareResourceType.NOTE, note_id, user_id):
                raise PermissionDeniedError("Access denied")
        return note

    @staticmethod
    def update_note(
        db: Session, note_id: str, user_id: str, data: dict[str, Any]
    ) -> Note:
        """Update an existing note.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.
            data (dict[str, Any]): The data.

        Returns:
            Note: Note result.
        """
        note = NoteService.get_note(db, note_id, user_id)
        if "content" in data and isinstance(data["content"], dict):
            content = cast(dict[str, Any], data["content"])
            data = {**data, "plain_text": content.get("text")}
        return NoteRepository.update(db, db_obj=note, update_data=data)

    @staticmethod
    def set_pinned(
        db: Session, note_id: str, user_id: str, pinned: bool
    ) -> Note:
        """Set pinned.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.
            pinned (bool): Pinned flag.

        Returns:
            Note: Note result.
        """
        note = NoteService.get_note(db, note_id, user_id)
        return NoteRepository.update(
            db, db_obj=note, update_data={"pinned": pinned}
        )

    @staticmethod
    def move_note(
        db: Session, note_id: str, user_id: str, folder_id: str | None
    ) -> Note:
        """Move a note to a different folder.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.
            folder_id (str | None): Unique identifier of the folder.

        Returns:
            Note: Note result.
        """
        note = NoteService.get_note(db, note_id, user_id)
        return NoteRepository.update(
            db, db_obj=note, update_data={"folder_id": folder_id}
        )

    @staticmethod
    def delete_note(db: Session, note_id: str, user_id: str) -> None:
        """Delete a note.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.

        Returns:
            None: None result.
        """
        note = NoteService.get_note(db, note_id, user_id)
        # Fixed: Pass the fetched model instance as db_obj
        NoteRepository.delete(db, db_obj=note)
