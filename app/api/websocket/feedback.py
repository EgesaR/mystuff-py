"""WebSocket endpoint pushing new feedback to connected developers in real time."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.database.session import SessionLocal
from app.repositories.user_repository import UserRepository

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
        """Remove a connection, e.g. after disconnect pr a failed send."""
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, str]) -> None:
        """Send a payload to every connected developer, pruning dead sockets."""
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


feedback_manager = FeedbackConnectionManager()


@router.websocket("/ws/feedback")
async def feedback_ws(websocket: WebSocket) -> None:
    """Developer-only socket that receives newly submitted feeback live."""
    token = websocket.query_params.get("token") or websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)
    if payload is None or not payload.sub:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()

    try:
        user = UserRepository.get(db, payload.sub)

        if not user or not getattr(user, "is_developer", False):
            return
    finally:
        db.close()

    await feedback_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive; ignore client messages
    except WebSocketDisconnect:
        feedback_manager.disconnect(websocket)
