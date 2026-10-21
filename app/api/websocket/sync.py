"""Authenticated real-time synchronization for editor snapshots."""

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketState

from app.api.deps.auth import get_current_user_ws_cookie
from app.api.deps.database import get_db
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


class SyncManager:
    """Track editor sockets per note within this API process."""

    def __init__(self) -> None:
        self.connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, note_id: UUID) -> bool:
        async with self._lock:
            room = self.connections[note_id]
            if len(room) >= MAX_ROOM_CONNECTIONS:
                await websocket.close(code=1013, reason="Note is at capacity")
                return False
            await websocket.accept()
            room.add(websocket)
            return True

    async def disconnect(self, websocket: WebSocket, note_id: UUID) -> None:
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
        for websocket in tuple(self.connections.get(note_id, ())):
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
    """Join a note room and exchange full snapshots using server revisions."""
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
                "Editor sync socket rejected: reason=note_access_denied "
                "note=%s user=%s",
                note_id,
                current_user.id,
            )
            await websocket.close(code=1008, reason="Note access denied")
            return

    if not await sync_manager.connect(websocket, note_id):
        return
    try:
        snapshot = read_snapshot(note) if note is not None else None
        if snapshot is None:
            if note is not None and note.content not in (None, {}):
                await websocket.send_json(
                    {"type": "error", "code": "legacy_note_content"}
                )
            else:
                await websocket.send_json({"type": "ready", "revision": 0})
        else:
            revision, document = snapshot
            await websocket.send_json(
                {
                    "type": "snapshot",
                    "revision": revision,
                    "document": document,
                }
            )

        window_start = time.monotonic()
        change_count = 0
        while True:
            raw_message = await websocket.receive_text()
            if len(raw_message.encode("utf-8")) > MAX_MESSAGE_BYTES:
                await websocket.close(code=1009, reason="Message too large")
                return
            try:
                parsed_message: object = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "code": "invalid_json"}
                )
                continue
            if not isinstance(parsed_message, dict):
                await websocket.send_json(
                    {"type": "error", "code": "unsupported_message"}
                )
                continue
            message = cast(dict[str, object], parsed_message)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if message.get("type") != "change":
                await websocket.send_json(
                    {"type": "error", "code": "unsupported_message"}
                )
                continue
            now = time.monotonic()
            if now - window_start >= 60:
                window_start = now
                change_count = 0
            change_count += 1
            if change_count > 60:
                await websocket.close(
                    code=1008,
                    reason="Too many snapshot updates",
                )
                return
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
                    {"type": "error", "code": "invalid_snapshot"}
                )
                continue

            try:
                revision, document = save_snapshot(
                    db,
                    note_id=note_id,
                    user=current_user,
                    payload=payload,
                )
            except LegacyNoteContentError:
                await websocket.send_json(
                    {"type": "error", "code": "legacy_note_content"}
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
                    {"type": "error", "code": "edit_access_required"}
                )
                continue
            except NotFoundError:
                await websocket.send_json(
                    {"type": "error", "code": "note_not_found"}
                )
                continue
            except EncryptionUnavailableError:
                await websocket.send_json(
                    {"type": "error", "code": "encryption_unavailable"}
                )
                continue
            except SnapshotIntegrityError:
                logger.exception(
                    "Stored editor snapshot integrity check failed"
                )
                await websocket.send_json(
                    {"type": "error", "code": "snapshot_unavailable"}
                )
                continue
            except ValueError:
                await websocket.send_json(
                    {"type": "error", "code": "invalid_snapshot"}
                )
                continue

            await websocket.send_json(
                {
                    "type": "ack",
                    "opId": payload.op_id,
                    "revision": revision,
                }
            )
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
        logger.info("Editor sync disconnected: note=%s user=%s", note_id, current_user.id)
    except (EncryptionUnavailableError, SnapshotIntegrityError):
        logger.exception("Unable to load editor snapshot: note=%s", note_id)
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason="Snapshot unavailable")
    finally:
        await sync_manager.disconnect(websocket, note_id)
