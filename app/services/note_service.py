"""Note business logic, access control, search and mutation operations."""

import re
from html.parser import HTMLParser
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import SharePermission, ShareResourceType
from app.models.folder import Folder
from app.models.note import Note
from app.repositories.note_repository import NoteRepository
from app.repositories.share_repository import ShareRepository

_EDITOR_SNAPSHOT_KEYS = {
    "_editor_snapshot_v1",
    "_editor_snapshot_v2",
}


class _PlainTextExtractor(HTMLParser):
    """Extract readable text while ignoring executable and style content."""

    _IGNORED_TAGS = {"script", "style", "noscript"}
    _BLOCK_TAGS = {
        "p",
        "div",
        "br",
        "li",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _strip_html(value: str | None) -> str | None:
    """Convert HTML content into normalized plain text."""
    if not value:
        return None

    parser = _PlainTextExtractor()
    parser.feed(value)
    parser.close()

    plain_text = re.sub(r"\s+", " ", "".join(parser.parts)).strip()
    return plain_text or None


def _extract_plain_text(content: Any) -> str | None:
    """Extract searchable text from a note's content payload."""
    if not isinstance(content, dict):
        return None

    payload = cast(dict[str, Any], content)
    text = payload.get("text")
    return _strip_html(text if isinstance(text, str) else None)


def _validate_folder_owner(
    db: Session,
    *,
    folder_id: UUID | None,
    user_id: UUID,
) -> None:
    """Ensure a note is only assigned to a folder owned by the user."""
    if folder_id is None:
        return

    folder = (
        db.query(Folder)
        .filter(
            Folder.id == folder_id,
            Folder.owner_id == user_id,
        )
        .first()
    )

    if folder is None:
        raise NotFoundError("Folder not found")


class NoteService:
    """Application rules for note access and management."""

    @staticmethod
    def _get_accessible_note(
        db: Session,
        note_id: UUID,
        user_id: UUID,
        *,
        require_edit: bool = False,
    ) -> Note:
        """Retrieve a note accessible through ownership or accepted sharing."""
        note = NoteRepository.get(db, note_id)

        if note is None:
            raise NotFoundError("Note not found")

        if note.owner_id == user_id:
            return note

        share = ShareRepository.get_accepted_for_resource(
            db,
            ShareResourceType.NOTE,
            note_id,
            user_id,
        )

        if share is None:
            raise PermissionDeniedError("Access denied")

        if require_edit and share.permission != SharePermission.EDIT:
            raise PermissionDeniedError("Edit access required")

        return note

    @staticmethod
    def require_edit_access(
        db: Session,
        note_id: UUID,
        user_id: UUID,
    ) -> Note:
        """Require ownership or an accepted share with edit permission."""
        return NoteService._get_accessible_note(
            db,
            note_id,
            user_id,
            require_edit=True,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    @staticmethod
    def list_notes(
        db: Session,
        user_id: UUID,
        *,
        folder_id: UUID | None = None,
        query_text: str | None = None,
        pinned_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Note]:
        return NoteRepository.get_user_notes(
            db,
            user_id,
            folder_id=folder_id,
            query_text=query_text,
            pinned_only=pinned_only,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def list_editor_notes(
        db: Session,
        user_id: UUID,
        *,
        folder_id: UUID | None = None,
        query: str | None = None,
        pinned_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Note]:
        """List notes for the editor's paginated, recently updated index."""
        return NoteRepository.get_editor_notes(
            db,
            user_id,
            folder_id=folder_id,
            query_text=query,
            pinned_only=pinned_only,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def list_pinned(
        db: Session,
        user_id: UUID,
        *,
        limit: int = 100,
    ) -> list[Note]:
        return NoteRepository.get_pinned_notes(
            db,
            user_id,
            limit=limit,
        )

    @staticmethod
    def search_notes(
        db: Session,
        user_id: UUID,
        query: str,
        *,
        limit: int = 100,
    ) -> list[Note]:
        return NoteRepository.search_notes(
            db,
            user_id,
            query,
            limit=limit,
        )

    @staticmethod
    def get_note(
        db: Session,
        note_id: UUID,
        user_id: UUID,
    ) -> Note:
        """Retrieve a single note accessible to the requesting user."""
        return NoteService._get_accessible_note(
            db,
            note_id,
            user_id,
        )

    # ------------------------------------------------------------------
    # Creation and updates
    # ------------------------------------------------------------------

    @staticmethod
    def create_note(
        db: Session,
        *,
        owner_id: UUID,
        title: str,
        content: dict[str, Any] | None,
        folder_id: UUID | None,
        color: str | None,
        note_id: UUID | None = None,
    ) -> Note:
        """Create a note and derive its searchable plain-text content."""
        _validate_folder_owner(
            db,
            folder_id=folder_id,
            user_id=owner_id,
        )

        note_data: dict[str, Any] = {
            "owner_id": owner_id,
            "title": title,
            "content": content,
            "plain_text": _extract_plain_text(content),
            "folder_id": folder_id,
            "color": color,
        }

        if note_id is not None:
            note_data["id"] = note_id

        return NoteRepository.create(
            db,
            obj_in=note_data,
        )

    @staticmethod
    def update_note(
        db: Session,
        note_id: UUID,
        user_id: UUID,
        data: dict[str, Any],
    ) -> Note:
        """Update a note while enforcing ownership and sharing permissions."""
        note = NoteService._get_accessible_note(
            db,
            note_id,
            user_id,
            require_edit=True,
        )

        update_data = dict(data)

        # Snapshot-based editor documents have their own update workflow.
        is_editor_document = isinstance(note.content, dict) and any(key in note.content for key in _EDITOR_SNAPSHOT_KEYS)

        if is_editor_document and {
            "title",
            "content",
        }.intersection(update_data):
            raise ValueError("Editor documents must be changed through editor-snapshot")

        # Folder changes are reserved for the note owner.
        if "folder_id" in update_data and update_data["folder_id"] != note.folder_id:
            if note.owner_id != user_id:
                raise PermissionDeniedError("Only the note owner can move it between folders")

            _validate_folder_owner(
                db,
                folder_id=update_data["folder_id"],
                user_id=user_id,
            )

        # Keep searchable plain text synchronized with HTML content.
        if "content" in update_data:
            update_data["plain_text"] = _extract_plain_text(update_data["content"])

        return NoteRepository.update(
            db,
            db_obj=note,
            update_data=update_data,
        )

    # ------------------------------------------------------------------
    # Note actions
    # ------------------------------------------------------------------

    @staticmethod
    def set_pinned(
        db: Session,
        note_id: UUID,
        user_id: UUID,
        pinned: bool,
    ) -> Note:
        """Pin or unpin a note."""
        note = NoteService._get_accessible_note(
            db,
            note_id,
            user_id,
            require_edit=True,
        )

        return NoteRepository.update(
            db,
            db_obj=note,
            update_data={"pinned": pinned},
        )

    @staticmethod
    def move_note(
        db: Session,
        note_id: UUID,
        user_id: UUID,
        folder_id: UUID | None,
    ) -> Note:
        """Move an owned note into another folder or remove it from a folder."""
        note = NoteService._get_accessible_note(
            db,
            note_id,
            user_id,
            require_edit=True,
        )

        if note.owner_id != user_id:
            raise PermissionDeniedError("Only the note owner can move it between folders")

        _validate_folder_owner(
            db,
            folder_id=folder_id,
            user_id=user_id,
        )

        return NoteRepository.update(
            db,
            db_obj=note,
            update_data={"folder_id": folder_id},
        )

    @staticmethod
    def delete_note(
        db: Session,
        note_id: UUID,
        user_id: UUID,
    ) -> None:
        """Delete a note. Only its owner is permitted to do so."""
        note = NoteService._get_accessible_note(
            db,
            note_id,
            user_id,
        )

        if note.owner_id != user_id:
            raise PermissionDeniedError("Only the owner can delete a note")

        NoteRepository.delete(
            db,
            db_obj=note,
        )
