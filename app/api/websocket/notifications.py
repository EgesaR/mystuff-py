# app/api/websocket/notifications.py
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token

logger = logging.getLogger("app")
router = APIRouter()


class NotificationManager:
    def __init__(self) -> None:
        self.connections: defaultdict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self.connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        conns = self.connections.get(user_id)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            del self.connections[user_id]

    async def push(self, user_id: str, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self.connections.get(user_id, []):
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(
                    f"Failed to send WS message to user {user_id}: {e}")
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, user_id)


notification_manager = NotificationManager()


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket) -> None:
    # 1. Read the token directly from the browser's cookies
    token = websocket.cookies.get("access_token")

    if not token:
        # Close connection before accepting if unauthenticated
        await websocket.close(code=1008)
        return

    # 2. Decode the token using your security utility
    token_data = decode_access_token(token)

    if token_data is None or not token_data.sub:
        await websocket.close(code=1008)
        return

    user_id = token_data.sub

    # 3. Connect the user
    await notification_manager.connect(websocket, user_id)

    try:
        while True:
            # Keep the connection open and listen for messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        notification_manager.disconnect(websocket, user_id)
