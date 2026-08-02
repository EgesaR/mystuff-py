"""Note service module managing business logic operations for notes."""

import re
from html import unescape
from typing import Any, cast

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import SharePermission, ShareResourceType
from app.models.note import Note
from app.repositories.note_repository import NoteRepository
from app.repositories.share_repository import ShareRepository

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str | None) -> str | None:
    """Reduce stored HTML content to plain text for search/preview

    Args:
        html (str | None): Raw HTML from the rich-text editor

    Returns:
        str | None: Plain text with tags removed and entities decoded.
    """
    if not html:
        return None
    text = _TAG_RE.sub(" ", html)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip() or None


class NoteService:
    """Service class encapsulating application logic for Note management."""

    @staticmethod
    def _get_accessible_note(
        db: Session, note_id: str, user_id: str, *, require_edit: bool = False
    ) -> Note:
        """Fetch a note the user owns or has an accepted share for.

        The owner always has full access. Non-owners must have an accepted
        share invitation. If ``require_edit`` is ``True``, the share must
        grant :class:`SharePermission.EDIT`; otherwise, view permission is
        sufficient.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the requesting user.
            require_edit (bool): Whether edit permission is required.

        Returns:
            Note: The accessible note.

        Raises:
            NotFoundError: If the note does not exist.
            PermissionDeniedError: If the user does not have the required
                ownership or sharing permissions.
        """
        note = NoteRepository.get(db, note_id)
        if not note:
            raise NotFoundError("Note not found")

        if note.owner_id == user_id:
            return note

        share = ShareRepository.get_accepted_for_resource(
            db, ShareResourceType.NOTE, note_id, user_id
        )
        if share is None:
            raise PermissionDeniedError("Access denied")
        if require_edit and share.permission != SharePermission.EDIT:
            raise PermissionDeniedError("View-only access")

        return note
    
    @staticmethod
    def require_edit_access(db: Session, note_id: str, user_id: str) -> Note:
        """Fetch a note the user can edit — ownership or an EDIT share.

        Public entry point for other services (e.g. MediaService) that need
        to gate a note-scoped action on edit permission without reaching
        into NoteService's private access-check helper.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the user.

        Returns:
            Note: The Note row.
        """
        return NoteService._get_accessible_note(
            db, note_id, user_id, require_edit=True
        )

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
            "plain_text": _strip_html((content or {}).get("text")),
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
        return NoteService._get_accessible_note(db, note_id, user_id)

    @staticmethod
    def update_note(
        db: Session, note_id: str, user_id: str, data: dict[str, Any]
    ) -> Note:
        """Update an existing note.

        The requesting user must either own the note or have an accepted
        share with edit permission.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the requesting user.
            data (dict[str, Any]): Fields to update.

        Returns:
            Note: The updated note.

        Raises:
            NotFoundError: If the note does not exist.
            PermissionDeniedError: If the user lacks edit permission.
        """
        note = NoteService._get_accessible_note(
            db, note_id, user_id, require_edit=True
        )
        if "content" in data and isinstance(data["content"], dict):
            content = cast(dict[str, Any], data["content"])
            data = {
                **data,
                "plain_text": _strip_html(
                    cast(str | None, content.get("text"))
                )
            }
        return NoteRepository.update(db, db_obj=note, update_data=data)

    @staticmethod
    def set_pinned(
        db: Session, note_id: str, user_id: str, pinned: bool
    ) -> Note:
        """Pin or unpin a note.

        The requesting user must own the note or have an accepted share with
        edit permission.

        ...
        Raises:
            NotFoundError: If the note does not exist.
            PermissionDeniedError: If the user lacks edit permission.
        """
        note = NoteService._get_accessible_note(
            db, note_id, user_id, require_edit=True
        )
        return NoteRepository.update(
            db, db_obj=note, update_data={"pinned": pinned}
        )

    @staticmethod
    def move_note(
        db: Session, note_id: str, user_id: str, folder_id: str | None
    ) -> Note:
        """Move a note to a different folder.

        The requesting user must own the note or have an accepted share with
        edit permission.

        ...
        Raises:
            NotFoundError: If the note does not exist.
            PermissionDeniedError: If the user lacks edit permission.
        """
        note = NoteService._get_accessible_note(db, note_id, user_id, require_edit=True)
        return NoteRepository.update(
            db, db_obj=note, update_data={"folder_id": folder_id}
        )

    @staticmethod
    def delete_note(db: Session, note_id: str, user_id: str) -> None:
        """Delete a note.

        Only the owner of a note may delete it. Shared users, including those
        with edit permission, cannot delete notes they do not own.

        Args:
            db (Session): Database session.
            note_id (str): Unique identifier of the note.
            user_id (str): Unique identifier of the requesting user.

        Raises:
            NotFoundError: If the note does not exist.
            PermissionDeniedError: If the user is not the owner.
        """
        note = NoteService._get_accessible_note(db, note_id, user_id)
        
        if note.owner_id != user_id:
            raise PermissionDeniedError(
                "Only the owner can delete a note"
            )
        NoteRepository.delete(db, db_obj=note)
