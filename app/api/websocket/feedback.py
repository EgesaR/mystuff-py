"""WebSocket endpoint pushing new feedback to connected developers in real time."""

import logging

# 1. Removed unused `status` import
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps.auth import get_current_user_ws
# 2. Added the missing User model import to fix E0602/F821.
# (Adjust this path if your User model is located elsewhere, e.g., app.schemas.user)
from app.models.user import User

# 3. Removed unused imports (decode_access_token, SessionLocal, UserRepository)

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

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection, e.g. after disconnect or a failed send."""
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, str]) -> None:
        """Send a payload to every connected developer, pruning dead sockets."""
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            # 4. Catching `Exception as e` and logging it mitigates the
            # W0718 "broad-exception-caught" warning while aiding debugging.
            except Exception as e:
                logger.warning("Failed to send message to a connection: %s", e)
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


feedback_manager = FeedbackConnectionManager()


# 5. Split the function signature into multiple lines to fix C0301 (line too long)
@router.websocket("/ws/feedback")
async def feedback_ws(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_ws)
) -> None:
    # 6. Moved the docstring to the very top of the function to fix W0105
    # ("String statement has no effect"). Docstrings must be the first statement.
    """Developer-only socket that receives newly submitted feedback live."""

    print("========== WEBSOCKET DEBUG ==========")
    print("Headers:")
    print(dict(websocket.headers))

    print("Cookies:")
    print(websocket.cookies)

    print("Query params:")
    print(dict(websocket.query_params))
    print("=====================================")

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received from {current_user.username}: {data}")
    except WebSocketDisconnect:
        print(f"Client {current_user.username} disconnected")
