"""Admin live-log telemetry WebSocket."""

import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("app")
router = APIRouter()


class ConnectionManager:
    """Manages active admin and per-user WebSocket connections."""

    def __init__(self) -> None:
        self.admin_connections: list[WebSocket] = []
        self.user_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect_admin(self, websocket: WebSocket) -> None:
        """Register a new admin connection."""
        await websocket.accept()
        self.admin_connections.append(websocket)
        logger.debug("telemetry: admin connected (total=%d)",
                     len(self.admin_connections))

    async def connect_user(self, websocket: WebSocket, user_id: str) -> None:
        """Register a new user connection."""
        await websocket.accept()
        self.user_connections[user_id].append(websocket)

    def disconnect_admin(self, websocket: WebSocket) -> None:
        """Remove an admin connection."""
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        logger.debug("telemetry: admin disconnected (total=%d)",
                     len(self.admin_connections))

    def disconnect_user(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a user connection."""
        connections = self.user_connections.get(user_id)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                del self.user_connections[user_id]

    async def broadcast_log(self, log_data: dict[str, Any]) -> None:
        """Push a log event to every connected admin socket."""
        payload: dict[str, Any] = {"type": "live_log", "data": log_data}
        dead: list[WebSocket] = []

        for ws in self.admin_connections:
            try:
                await ws.send_json(payload)
            except (RuntimeError, ConnectionError):
                dead.append(ws)

        for ws in dead:
            self.disconnect_admin(ws)

    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> None:
        """Push a payload to all sockets belonging to one user."""
        connections = list(self.user_connections.get(user_id, []))
        dead: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_json(payload)
            except (RuntimeError, ConnectionError):
                dead.append(ws)

        for ws in dead:
            self.disconnect_user(ws, user_id)


manager = ConnectionManager()


@router.websocket("/ws/admin/telemetry")
async def admin_telemetry(websocket: WebSocket) -> None:
    """Admin live-log telemetry stream."""
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError, ConnectionError):
        manager.disconnect_admin(websocket)
