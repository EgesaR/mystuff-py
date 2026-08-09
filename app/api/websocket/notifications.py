"""WebSocket endpoint for real-time user notifications."""

import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps.auth import get_current_user_ws
from app.models.user import User

logger = logging.getLogger("app")
router = APIRouter()


class NotificationManager:
    """Tracks active notification WebSocket connections per user."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)
        logger.info(
            "Notification WS connected – user=%s total=%d",
            user_id,
            len(self._connections[user_id]),
        )

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        conns = self._connections.get(user_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            del self._connections[user_id]
        logger.info(
            "Notification WS disconnected – user=%s remaining=%d",
            user_id,
            len(self._connections.get(user_id, [])),
        )

    async def push(self, user_id: str, payload: dict[str, Any]) -> None:
        """Send a payload to every active connection for a user."""
        dead: list[WebSocket] = []
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning("Failed to push to user %s: %s", user_id, exc)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)


notification_manager = NotificationManager()


@router.websocket("/ws/notifications")
async def notifications_ws(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_ws),
) -> None:
    """
    Authenticated notification socket.
    Token is taken from ?token=... (production) or access_token cookie (local).
    """
    user_id = current_user.id
    await notification_manager.connect(websocket, user_id)

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except TimeoutError:
                logger.info("Notification WS timeout – user=%s", user_id)
                break
    except WebSocketDisconnect:
        logger.info("Notification WS closed – user=%s", user_id)
    finally:
        notification_manager.disconnect(websocket, user_id)
