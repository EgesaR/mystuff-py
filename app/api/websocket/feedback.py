"""WebSocket endpoint pushing new feedback to connected developers in real time."""

import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps.auth import require_developer_ws
from app.models.user import User

logger = logging.getLogger("app")
router = APIRouter()


class FeedbackConnectionManager:
    """Tracks active developer WebSocket connections for feedback broadcasts."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new developer connection."""
        await websocket.accept()
        self._connections.add(websocket)
        logger.info(
            "Developer connected. Total connections: %d",
            len(self._connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection, e.g. after disconnect or a failed send."""
        self._connections.discard(websocket)
        logger.info(
            "Developer disconnected. Total connections: %d",
            len(self._connections)
        )

    async def broadcast(self, payload: dict[str, str]) -> None:
        """Send a payload to every connected developer, pruning dead sockets."""
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(
                    "Failed to send message to a connection: %s",
                    e
                )
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


feedback_manager = FeedbackConnectionManager()


@router.websocket("/ws/feedback")
async def feedback_ws(
    websocket: WebSocket,
    current_user: User = Depends(require_developer_ws)
) -> None:
    """Developer-only socket that receives newly submitted feedback live."""

    await feedback_manager.connect(websocket)
    try:
        while True:
            try:
                # Wait for client message (including heartbeat pings)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # force disconnect if client is silent
                )

                # Apllication-level heartbeat
                if data == "ping":
                    await websocket.send_text("pong")
                    continue

                # You can handle other client -> server messages here if need
                logger.debug(
                    "Received from %s: %s",
                    current_user.username,
                    data
                )
                await websocket.send_text(f"Message received from {current_user.username}: {data}")
                # await websocket.send_json({"type": "ack", "message": data})
            except TimeoutError:
                # No messages received in time -> client is probably dead
                logger.info("Heatbeat timeout for %s", current_user.username)
                break

    except WebSocketDisconnect:
        logger.info(
            "Client %s disconnected",
            current_user.username
        )
        print(f"Client {current_user.username} disconnected")
    finally:
        feedback_manager.disconnect(websocket)
