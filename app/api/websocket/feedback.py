import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps.auth import require_developer_ws
from app.models.user import User

"""WebSocket endpoint pushing new feedback to connected developers in real time."""


logger = logging.getLogger("app")

router = APIRouter()


class FeedbackConnectionManager:
    """Tracks active developer WebSocket connections."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new developer connection."""
        await websocket.accept()

        self._connections.add(websocket)

        logger.info(
            "Developer connected. Total connections: %d",
            len(self._connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections.discard(websocket)

        logger.info(
            "Developer disconnected. Total connections: %d",
            len(self._connections),
        )

    async def broadcast(
        self,
        payload: dict[str, str],
    ) -> None:
        """Broadcast a payload to all connected developers."""

        async def send(
            connection: WebSocket,
        ) -> WebSocket | None:
            try:
                await connection.send_json(payload)
                return None

            except Exception as exc:
                logger.warning(
                    "Failed to send message to WebSocket: %s",
                    exc,
                )
                return connection

        results = await asyncio.gather(
            *(send(connection) for connection in self._connections)
        )

        for connection in results:
            if connection is not None:
                self.disconnect(connection)


feedback_manager = FeedbackConnectionManager()


@router.websocket("/ws/feedback")
async def feedback_ws(
    websocket: WebSocket,
    current_user: User = Depends(require_developer_ws),
) -> None:
    """
    Developer-only WebSocket.

    Authentication is performed before this endpoint executes
    through the require_developer_ws dependency.
    """
    logger.info("WS accepted for user %s (developer=%s)",
            current_user.id, current_user.is_developer)
    await feedback_manager.connect(websocket)

    logger.info(
        "Feedback WebSocket established for developer: %s",
        current_user.username,
    )

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,
                )

                # Application-level heartbeat.
                if data == "ping":
                    await websocket.send_text("pong")
                    continue

                logger.debug(
                    "Received WebSocket message from %s: %s",
                    current_user.username,
                    data,
                )

            except TimeoutError:
                logger.info(
                    "Heartbeat timeout for developer: %s",
                    current_user.username,
                )
                break

    except WebSocketDisconnect:
        logger.info(
            "Developer WebSocket disconnected: %s",
            current_user.username,
        )

    except Exception:
        logger.exception(
            "Unexpected WebSocket error for developer: %s",
            current_user.username,
        )

    finally:
        feedback_manager.disconnect(websocket)
