"""Authenticated real-time synchronization for editor snapshots."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketState

from app.api.deps.auth import get_current_user_ws_cookie
from app.api.deps.database import get_db
from app.core.config import settings
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.user import User
from app.schemas.editor_sync import EditorSnapshotPayload
from app.services.editor_sync_service import (
    EncryptionUnavailableError,
    LegacyNoteContentError,
    SnapshotConflictError,
    SnapshotIntegrityError,
    get_accessible_note,
    get_note_if_present,
    read_snapshot,
    save_snapshot,
)

logger = logging.getLogger("app")

router = APIRouter()

MAX_ROOM_CONNECTIONS = 32
MAX_MESSAGE_BYTES = 1_000_000
MAX_CHANGES_PER_MINUTE = 60
RATE_LIMIT_WINDOW_SECONDS = 60


def _origin_key(value: str) -> tuple[str, str, int] | None:
    """Normalize an HTTP origin for strict allow-list comparison."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname

    if scheme not in {"http", "https"} or not hostname or parsed.username is not None or parsed.password is not None or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None

    try:
        port = parsed.port
    except ValueError:
        return None

    if port is None:
        port = 443 if scheme == "https" else 80

    return scheme, hostname.rstrip(".").lower(), port


def _origin_allowed(websocket: WebSocket) -> bool:
    """Check whether the WebSocket handshake originates from an allowed site."""
    origin = websocket.headers.get("origin")

    if not origin:
        return False

    requested = _origin_key(origin)

    if requested is None:
        return False

    allowed = {key for configured in settings.ALLOWED_ORIGINS if (key := _origin_key(configured)) is not None}

    return requested in allowed


class SyncManager:
    """Track connected editor clients per note within this API process."""

    def __init__(self) -> None:
        self.connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        note_id: UUID,
    ) -> bool:
        """Accept a socket if the note has available connection capacity."""
        at_capacity = False

        async with self._lock:
            room = self.connections.get(note_id)

            if room is not None and len(room) >= MAX_ROOM_CONNECTIONS:
                at_capacity = True
            else:
                await websocket.accept()
                self.connections[note_id].add(websocket)

        if at_capacity:
            await websocket.close(
                code=1013,
                reason="Note is at capacity",
            )
            return False

        return True

    async def disconnect(
        self,
        websocket: WebSocket,
        note_id: UUID,
    ) -> None:
        """Remove a socket and clean up empty note rooms."""
        async with self._lock:
            room = self.connections.get(note_id)

            if room is None:
                return

            room.discard(websocket)

            if not room:
                self.connections.pop(note_id, None)

    async def broadcast(
        self,
        note_id: UUID,
        sender: WebSocket,
        payload: dict[str, object],
    ) -> None:
        """Broadcast a committed snapshot to other connected clients."""
        connections = tuple(self.connections.get(note_id, ()))

        for websocket in connections:
            if websocket is sender:
                continue

            try:
                await websocket.send_json(payload)

            except (RuntimeError, OSError, WebSocketDisconnect):
                await self.disconnect(websocket, note_id)


sync_manager = SyncManager()


@router.websocket("/ws/sync/{note_id}")
async def editor_sync_ws(
    websocket: WebSocket,
    note_id: UUID,
    current_user: User = Depends(get_current_user_ws_cookie),
    db: Session = Depends(get_db),
) -> None:
    """Join a note room and exchange encrypted editor snapshots.

    Supports:
        - Cookie-based WebSocket authentication.
        - Origin allow-list validation.
        - Ownership and accepted-share access control.
        - Snapshot revision synchronization.
        - Optimistic concurrency conflict handling.
        - Per-connection update rate limiting.
        - Snapshot broadcasting to other connected clients.
    """

    # ---------------------------------------------------------------
    # Origin validation
    # ---------------------------------------------------------------
    # CORS middleware does not independently protect WebSocket
    # handshakes. Validate the Origin header explicitly.

    if not _origin_allowed(websocket):
        await websocket.close(
            code=1008,
            reason="Origin not allowed",
        )
        return

    # ---------------------------------------------------------------
    # Note access
    # ---------------------------------------------------------------

    note = get_note_if_present(db, note_id)

    if note is not None:
        try:
            note = get_accessible_note(
                db,
                note_id=note_id,
                user_id=current_user.id,
            )

        except (NotFoundError, PermissionDeniedError):
            logger.warning(
                "Editor sync rejected: access denied note=%s user=%s",
                note_id,
                current_user.id,
            )

            await websocket.close(
                code=1008,
                reason="Note access denied",
            )
            return

    # ---------------------------------------------------------------
    # Connection registration
    # ---------------------------------------------------------------

    if not await sync_manager.connect(websocket, note_id):
        return

    try:
        # -----------------------------------------------------------
        # Initial snapshot synchronization
        # -----------------------------------------------------------

        snapshot = read_snapshot(note) if note is not None else None

        if snapshot is None:
            if note is not None and note.content not in (None, {}):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "legacy_note_content",
                    }
                )
            else:
                await websocket.send_json(
                    {
                        "type": "ready",
                        "revision": 0,
                    }
                )

        else:
            revision, document = snapshot

            await websocket.send_json(
                {
                    "type": "snapshot",
                    "revision": revision,
                    "document": document,
                }
            )

        # -----------------------------------------------------------
        # Per-connection rate limiting
        # -----------------------------------------------------------

        window_start = time.monotonic()
        change_count = 0

        # -----------------------------------------------------------
        # Message processing
        # -----------------------------------------------------------

        while True:
            raw_message = await websocket.receive_text()

            if len(raw_message.encode("utf-8")) > MAX_MESSAGE_BYTES:
                await websocket.close(
                    code=1009,
                    reason="Message too large",
                )
                return

            # -------------------------------------------------------
            # JSON decoding
            # -------------------------------------------------------

            try:
                parsed_message: object = json.loads(raw_message)

            except (json.JSONDecodeError, RecursionError):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_json",
                    }
                )
                continue

            if not isinstance(parsed_message, dict):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "unsupported_message",
                    }
                )
                continue

            message = cast(dict[str, object], parsed_message)
            message_type = message.get("type")

            # -------------------------------------------------------
            # Heartbeat
            # -------------------------------------------------------

            if message_type == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                    }
                )
                continue

            # -------------------------------------------------------
            # Message type validation
            # -------------------------------------------------------

            if message_type != "change":
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "unsupported_message",
                    }
                )
                continue

            # -------------------------------------------------------
            # Rate limiting
            # -------------------------------------------------------

            now = time.monotonic()

            if now - window_start >= RATE_LIMIT_WINDOW_SECONDS:
                window_start = now
                change_count = 0

            change_count += 1

            if change_count > MAX_CHANGES_PER_MINUTE:
                await websocket.close(
                    code=1008,
                    reason="Too many snapshot updates",
                )
                return

            # -------------------------------------------------------
            # Snapshot payload validation
            # -------------------------------------------------------

            try:
                payload = EditorSnapshotPayload.model_validate(
                    {
                        "baseRevision": message.get("baseRevision"),
                        "document": message.get("document"),
                        "opId": message.get("opId"),
                    }
                )

            except ValidationError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_snapshot",
                    }
                )
                continue

            # -------------------------------------------------------
            # Snapshot persistence
            # -------------------------------------------------------

            try:
                revision, document = save_snapshot(
                    db,
                    note_id=note_id,
                    user=current_user,
                    payload=payload,
                )

            except LegacyNoteContentError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "legacy_note_content",
                    }
                )
                continue

            except SnapshotConflictError as exc:
                await websocket.send_json(
                    {
                        "type": "conflict",
                        "opId": payload.op_id,
                        "revision": exc.revision,
                        "document": exc.document,
                    }
                )
                continue

            except PermissionDeniedError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "edit_access_required",
                    }
                )
                continue

            except NotFoundError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "note_not_found",
                    }
                )
                continue

            except EncryptionUnavailableError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "encryption_unavailable",
                    }
                )
                continue

            except SnapshotIntegrityError:
                logger.exception(
                    "Editor snapshot integrity check failed: note=%s",
                    note_id,
                )

                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "snapshot_unavailable",
                    }
                )
                continue

            except ValueError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_snapshot",
                    }
                )
                continue

            # -------------------------------------------------------
            # Acknowledgement
            # -------------------------------------------------------

            await websocket.send_json(
                {
                    "type": "ack",
                    "opId": payload.op_id,
                    "revision": revision,
                }
            )

            # -------------------------------------------------------
            # Broadcast committed snapshot
            # -------------------------------------------------------

            await sync_manager.broadcast(
                note_id,
                websocket,
                {
                    "type": "snapshot",
                    "revision": revision,
                    "document": document,
                },
            )

    except WebSocketDisconnect:
        logger.info(
            "Editor sync disconnected: note=%s user=%s",
            note_id,
            current_user.id,
        )

    except (EncryptionUnavailableError, SnapshotIntegrityError):
        logger.exception(
            "Unable to load editor snapshot: note=%s",
            note_id,
        )

        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(
                code=1011,
                reason="Snapshot unavailable",
            )

    finally:
        await sync_manager.disconnect(websocket, note_id)
