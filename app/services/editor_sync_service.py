"""Encrypted persistence and revision checks for editor snapshots."""

from __future__ import annotations

import binascii
import hashlib
import hmac
import json
import math
import secrets
from typing import Any, cast
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.note import Note
from app.models.user import User
from app.schemas.editor_sync import EditorSnapshotPayload
from app.services.note_service import NoteService

SNAPSHOT_KEY = "_editor_snapshot_v1"
MAX_SNAPSHOT_BYTES = 1_000_000
AES_GCM_NONCE_BYTES = 12
AES_GCM_TAG_BYTES = 16
MAX_CIPHERTEXT_BYTES = MAX_SNAPSHOT_BYTES + AES_GCM_TAG_BYTES
MAX_SAFE_INTEGER = 9_007_199_254_740_991

BLOCK_TYPES = {
    "paragraph",
    "heading",
    "bullet",
    "numbered",
    "todo",
    "quote",
    "callout",
    "code",
    "divider",
    "image",
    "table",
    "math",
    "embed",
}
THEMES = {"paper", "night", "manuscript", "contrast"}
ALIGNMENTS = {"left", "center", "right", "justify"}


class EncryptionUnavailableError(RuntimeError):
    """Raised when note encryption is not configured safely."""


class SnapshotIntegrityError(RuntimeError):
    """Raised when a stored snapshot cannot be authenticated or decoded."""


class LegacyNoteContentError(RuntimeError):
    """Raised when editor sync would overwrite a legacy note body."""


class SnapshotConflictError(RuntimeError):
    """Raised when the client is editing from an outdated server revision."""

    def __init__(
        self,
        revision: int,
        document: dict[str, Any] | None,
    ) -> None:
        super().__init__("The editor snapshot has changed on the server")
        self.revision = revision
        self.document = document


def is_editor_snapshot(content: object) -> bool:
    """Return whether note content contains a server-encrypted snapshot."""
    return isinstance(content, dict) and SNAPSHOT_KEY in content


def _aesgcm() -> AESGCM:
    """Build the AES-GCM cipher from the dedicated snapshot encryption key."""
    configured = settings.NOTE_ENCRYPTION_KEY
    if configured is None:
        raise EncryptionUnavailableError("NOTE_ENCRYPTION_KEY is not configured")

    secret = configured.get_secret_value()
    application_secret = settings.SECRET_KEY
    if len(secret) < 32 or hmac.compare_digest(
        secret.encode("utf-8"),
        application_secret.encode("utf-8"),
    ):
        raise EncryptionUnavailableError("NOTE_ENCRYPTION_KEY must be a separate secret of at least 32 characters")

    key = hashlib.sha256(b"mystuff:editor-snapshot:v1:" + secret.encode("utf-8")).digest()
    return AESGCM(key)


def _associated_data(note_id: UUID, owner_id: UUID) -> bytes:
    """Bind encrypted snapshot data to its note and owner."""
    return f"editor-snapshot:v1:{note_id}:{owner_id}".encode("ascii")


def _validate_document(
    document: dict[str, Any],
    note_id: UUID,
) -> None:
    """Validate the editor document before it is persisted."""
    if document.get("id") != str(note_id):
        raise ValueError("Document ID must match the note ID")

    title = document.get("title")
    if not isinstance(title, str) or len(title) > 255:
        raise ValueError("Document title must be 255 characters or fewer")

    if document.get("encrypted") is not True:
        raise ValueError("Editor document must be marked encrypted")

    encryption_mode = document.get("encryptionMode")
    if not isinstance(encryption_mode, str) or encryption_mode not in {
        "standard",
        "vault",
    }:
        raise ValueError("Editor document has an invalid encryption mode")

    theme = document.get("theme")
    if not isinstance(theme, str) or theme not in THEMES:
        raise ValueError("Editor document has an invalid theme")

    for name in ("createdAt", "updatedAt", "revision"):
        value = document.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or value > MAX_SAFE_INTEGER or (isinstance(value, float) and not math.isfinite(value)):
            raise ValueError(f"Editor document has an invalid {name}")

    if not isinstance(document["revision"], int):
        raise ValueError("Editor document has an invalid revision")

    blocks_value = document.get("blocks")
    if not isinstance(blocks_value, list):
        raise ValueError("Editor document has an invalid block list")

    blocks = cast(list[Any], blocks_value)
    if len(blocks) > 10_000:
        raise ValueError("Editor document has an invalid block list")

    block_ids: set[str] = set()

    for block_value in blocks:
        if not isinstance(block_value, dict):
            raise ValueError("Editor document contains an invalid block")

        block = cast(dict[str, Any], block_value)
        block_id = block.get("id")
        block_type = block.get("type")
        block_html = block.get("html")

        if not isinstance(block_id, str) or not block_id or block_id in block_ids or not isinstance(block_html, str) or not isinstance(block_type, str) or block_type not in BLOCK_TYPES:
            raise ValueError("Editor document contains an invalid block")

        block_ids.add(block_id)

        alignment = block.get("alignment", "left")
        if alignment is not None and (not isinstance(alignment, str) or alignment not in ALIGNMENTS):
            raise ValueError("Editor document contains an invalid alignment")

        font_family = block.get("fontFamily")
        if font_family is not None and (not isinstance(font_family, str) or len(font_family) > 128):
            raise ValueError("Editor document contains an invalid font family")

        font_size = block.get("fontSize")
        if font_size is not None and (
            isinstance(font_size, bool) or not isinstance(font_size, (int, float)) or not 8 <= font_size <= 96 or (isinstance(font_size, float) and not math.isfinite(font_size))
        ):
            raise ValueError("Editor document contains an invalid font size")


def _snapshot_parts(note: Note) -> tuple[int, str, str] | None:
    """Extract and structurally validate the stored v1 envelope fields."""
    content = note.content
    if not isinstance(content, dict) or SNAPSHOT_KEY not in content:
        return None

    content_data = cast(dict[str, Any], content)
    envelope_value = content_data[SNAPSHOT_KEY]
    if not isinstance(envelope_value, dict):
        raise SnapshotIntegrityError("Stored snapshot envelope is invalid")

    envelope = cast(dict[str, Any], envelope_value)
    revision = envelope.get("revision")
    nonce = envelope.get("nonce")
    ciphertext = envelope.get("ciphertext")

    if (
        not isinstance(revision, int)
        or isinstance(revision, bool)
        or not 1 <= revision <= MAX_SAFE_INTEGER
        or not isinstance(nonce, str)
        or len(nonce) != AES_GCM_NONCE_BYTES * 2
        or not isinstance(ciphertext, str)
        or len(ciphertext) < AES_GCM_TAG_BYTES * 2
        or len(ciphertext) > MAX_CIPHERTEXT_BYTES * 2
        or len(ciphertext) % 2 != 0
    ):
        raise SnapshotIntegrityError("Stored snapshot envelope is invalid")

    return revision, nonce, ciphertext


def decrypt_snapshot(note: Note) -> tuple[int, dict[str, Any]] | None:
    """Decrypt a note snapshot and return its server revision and document."""
    parts = _snapshot_parts(note)
    if parts is None:
        return None

    revision, nonce_hex, ciphertext_hex = parts

    try:
        nonce = binascii.unhexlify(nonce_hex)
        ciphertext = binascii.unhexlify(ciphertext_hex)
        plaintext = _aesgcm().decrypt(
            nonce,
            ciphertext,
            _associated_data(note.id, note.owner_id),
        )
        if len(plaintext) > MAX_SNAPSHOT_BYTES:
            raise SnapshotIntegrityError("Stored snapshot exceeds the size limit")
        parsed_document: object = json.loads(plaintext)
    except (ValueError, InvalidTag) as exc:
        raise SnapshotIntegrityError("Stored snapshot failed authentication or decoding") from exc

    if not isinstance(parsed_document, dict):
        raise SnapshotIntegrityError("Stored snapshot document is invalid")

    return revision, cast(dict[str, Any], parsed_document)


def _encrypt_snapshot(
    note: Note,
    revision: int,
    document: dict[str, Any],
) -> dict[str, Any]:
    """Encrypt a validated editor document into the v1 storage envelope."""
    plaintext = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    if len(plaintext) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Editor snapshot exceeds the 1 MB limit")

    nonce = secrets.token_bytes(AES_GCM_NONCE_BYTES)
    ciphertext = _aesgcm().encrypt(
        nonce,
        plaintext,
        _associated_data(note.id, note.owner_id),
    )

    return {
        SNAPSHOT_KEY: {
            "revision": revision,
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
        }
    }


def read_snapshot(note: Note) -> tuple[int, dict[str, Any]] | None:
    """Read a snapshot from an already-authorized note model."""
    return decrypt_snapshot(note)


def save_snapshot(
    db: Session,
    *,
    note_id: UUID,
    user: User,
    payload: EditorSnapshotPayload,
) -> tuple[int, dict[str, Any]]:
    """Persist a snapshot after authorization and optimistic revision checks."""
    document = payload.document
    _validate_document(document, note_id)

    encoded_document = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded_document) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Editor snapshot exceeds the 1 MB limit")

    title = cast(str, document["title"])
    note = db.query(Note).filter(Note.id == note_id).with_for_update().first()
    creating = note is None

    try:
        if note is None:
            if payload.base_revision != 0:
                raise SnapshotConflictError(0, None)

            note = Note(
                id=note_id,
                owner_id=user.id,
                title=title,
                content=None,
                plain_text=None,
            )
            db.add(note)
            current_revision = 0
        else:
            NoteService.require_edit_access(db, note_id, user.id)
            existing = decrypt_snapshot(note)

            if existing is None and note.content not in (None, {}):
                raise LegacyNoteContentError("Existing note content must be migrated before editor sync")

            current_revision = existing[0] if existing is not None else 0

        if payload.base_revision != current_revision:
            current = decrypt_snapshot(note)
            raise SnapshotConflictError(
                current_revision,
                current[1] if current is not None else None,
            )

        next_revision = current_revision + 1
        note.title = title
        note.content = _encrypt_snapshot(note, next_revision, document)
        # Encrypted editor content must not be duplicated into plain-text search.
        note.plain_text = None

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()

            if creating:
                concurrent_note = db.query(Note).filter(Note.id == note_id).first()
                if concurrent_note is not None:
                    NoteService.require_edit_access(db, note_id, user.id)
                    current = decrypt_snapshot(concurrent_note)
                    raise SnapshotConflictError(
                        current[0] if current is not None else 0,
                        current[1] if current is not None else None,
                    ) from exc

            raise

        db.refresh(note)
        return next_revision, document
    except Exception:
        db.rollback()
        raise


def get_accessible_note(
    db: Session,
    *,
    note_id: UUID,
    user_id: UUID,
) -> Note:
    """Return a note the user is permitted to view."""
    return NoteService.get_note(db, note_id, user_id)


def get_note_if_present(db: Session, note_id: UUID) -> Note | None:
    """Look up a note without applying access policy."""
    return db.query(Note).filter(Note.id == note_id).first()


def snapshot_revision(note: Note) -> int:
    """Read snapshot revision metadata without decrypting the document."""
    parts = _snapshot_parts(note)
    return parts[0] if parts is not None else 0
