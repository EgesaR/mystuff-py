# app/api/websocket/notifications.py

import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token

logger = logging.getLogger("app")
router = APIRouter()


class NotificationManager:
    """Manage active WebSocket notification connections."""

    def __init__(self) -> None:
        """Initialize the notification manager."""
        self.connections: defaultdict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            user_id: Unique identifier of the user.
        """
        await websocket.accept()
        self.connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            user_id: Unique identifier of the user.
        """
        conns = self.connections.get(user_id)
        if not conns:
            return

        if websocket in conns:
            conns.remove(websocket)

        if not conns:
            del self.connections[user_id]

    async def push(self, user_id: str, payload: dict[str, Any]) -> None:
        """Send a notification to all active connections for a user.

        Args:
            user_id: Unique identifier of the user.
            payload: Notification payload.
        """
        dead: list[WebSocket] = []

        for ws in self.connections.get(user_id, []):
            try:
                await ws.send_json(payload)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Failed to send WebSocket message to user %s: %s",
                    user_id,
                    exc,
                )
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, user_id)


notification_manager = NotificationManager()


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket) -> None:
    """Handle the notifications WebSocket endpoint.

    Authentication is performed using either:
    - the `token` query parameter, or
    - the `access_token` cookie.
    """
    token = (
        websocket.query_params.get("token")
        or websocket.cookies.get("access_token")
    )

    if not token:
        await websocket.close(code=1008)
        return

    token_data = decode_access_token(token)

    if token_data is None or not token_data.sub:
        await websocket.close(code=1008)
        return

    user_id = token_data.sub

    await notification_manager.connect(websocket, user_id)

    try:
        while True:
            # Keep the connection alive by receiving messages.
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for user %s", user_id)
        notification_manager.disconnect(websocket, user_id)

    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception(
            "Unexpected WebSocket error for user %s",
            user_id,
        )
        notification_manager.disconnect(websocket, user_id)
