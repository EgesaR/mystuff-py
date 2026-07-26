"""api/routes/logs.py
System log search (REST) + live telemetry (WebSocket) + accuracy stats.
"""

import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.models.user import User
from app.repositories.log_repository import LogRepository
from app.schemas.system_log import SystemLogResponse
from app.services.log_service import LogService

logger = logging.getLogger("app")

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket Connection Manager
# ══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manages active WebSocket connections for live log telemetry."""

    def __init__(self) -> None:
        """Init.
        
        Returns:
            None: None result.
        """
        self.admin_connections: list[WebSocket] = []
        self.user_connections: defaultdict[str,
                                           list[WebSocket]] = defaultdict(list)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect_admin(self, websocket: WebSocket) -> None:
        """Connect admin.
        
        Args:
            websocket (WebSocket): The websocket.
        
        Returns:
            None: None result.
        """
        await websocket.accept()
        self.admin_connections.append(websocket)

    async def connect_user(self, websocket: WebSocket, user_id: str) -> None:
        """Connect user.
        
        Args:
            websocket (WebSocket): The websocket.
            user_id (str): Unique identifier of the user.
        
        Returns:
            None: None result.
        """
        await websocket.accept()
        self.user_connections[user_id].append(websocket)

    def disconnect_admin(self, websocket: WebSocket) -> None:
        """Disconnect admin.
        
        Args:
            websocket (WebSocket): The websocket.
        
        Returns:
            None: None result.
        """
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)

    def disconnect_user(self, websocket: WebSocket, user_id: str) -> None:
        """Disconnect user.
        
        Args:
            websocket (WebSocket): The websocket.
            user_id (str): Unique identifier of the user.
        
        Returns:
            None: None result.
        """
        connections = self.user_connections.get(user_id)
        if not connections:
            return
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            del self.user_connections[user_id]

    # ── Broadcasting ──────────────────────────────────────────────────────────

    async def broadcast_log(self, log_data: dict[str, Any]) -> None:
        """Broadcast log.
        
        Args:
            log_data (dict[str, Any]): The log data.
        
        Returns:
            None: None result.
        """
        dead: list[WebSocket] = []
        payload = {"type": "live_log", "data": log_data}

        for ws in self.admin_connections:
            try:
                await ws.send_json(payload)
            except (RuntimeError, ConnectionError):
                dead.append(ws)

        for ws in dead:
            self.disconnect_admin(ws)

    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> None:
        """Send to user.
        
        Args:
            user_id (str): Unique identifier of the user.
            payload (dict[str, Any]): Request payload.
        
        Returns:
            None: None result.
        """
        connections = self.user_connections.get(user_id, [])
        dead: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_json(payload)
            except (RuntimeError, ConnectionError):
                dead.append(ws)

        for ws in dead:
            self.disconnect_user(ws, user_id)

    # ── Stats ────────────────────────────────═════════════════════════════════

    @property
    def total_admin_connections(self) -> int:
        """Total admin connections.
        
        Returns:
            int: int result.
        """
        return len(self.admin_connections)

    @property
    def total_user_connections(self) -> int:
        """Total user connections.
        
        Returns:
            int: int result.
        """
        return sum(len(v) for v in self.user_connections.values())


# Module-level singleton
manager = ConnectionManager()


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket endpoint
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/admin/telemetry")
async def admin_telemetry(websocket: WebSocket) -> None:
    """Admin telemetry.
    
    Args:
        websocket (WebSocket): The websocket.
    
    Returns:
        None: None result.
    """
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError, ConnectionError):
        manager.disconnect_admin(websocket)


# ══════════════════════════════════════════════════════════════════════════════
# REST log search
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/search",
    summary="Search system logs (admin / debugging)",
    response_model=list[SystemLogResponse],
)
def search_logs(
    user_id: str | None = Query(None, description="Filter by user ID"),
    regex_pattern: str | None = Query(
        None, description="PostgreSQL regex applied to log message"
    ),
    limit: int = Query(100, le=500),
    _current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Any]:
    """Search logs.
    
    Args:
        user_id (str | None): Unique identifier of the user.
        regex_pattern (str | None): The regex pattern.
        limit (int): Limit integer.
        _current_user (User): The  current user.
        db (Session): Database session.
    
    Returns:
        list[Any]: List of Any.
    """
    return LogService.search(
        db,
        user_id=user_id,
        regex_pattern=regex_pattern,
        limit=limit,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Word-accuracy stats (speech / lyrics transcription)
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/accuracy",
    summary="Aggregated word-accuracy stats for speech/lyrics transcription",
)
def accuracy_stats(
    mode: str | None = Query(
        None, pattern="^(speech|lyrics)$", description="Filter by transcription mode"
    ),
    accuracy_type: str | None = Query(
        None,
        pattern="^(raw_vs_processed|processed_vs_corrected)$",
        description=(
            "raw_vs_processed = pipeline output vs raw ASR (reference-free); "
            "processed_vs_corrected = what the user was shown vs their edit"
        ),
    ),
    user_id: str | None = Query(None, description="Filter by user ID"),
    limit: int = Query(500, le=2000),
    _current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Accuracy stats.
    
    Args:
        mode (str | None): The mode.
        accuracy_type (str | None): The accuracy type.
        user_id (str | None): Unique identifier of the user.
        limit (int): Limit integer.
        _current_user (User): The  current user.
        db (Session): Database session.
    
    Returns:
        dict[str, Any]: Response payload.
    """
    return LogService.get_accuracy_stats(
        db,
        mode=mode,
        accuracy_type=accuracy_type,
        user_id=user_id,
        limit=limit,
    )


@router.get(
    "/accuracy/history",
    summary="Raw word-accuracy log entries, newest first",
    response_model=list[SystemLogResponse],
)
def accuracy_history(
    mode: str | None = Query(None, pattern="^(speech|lyrics)$"),
    accuracy_type: str | None = Query(
        None, pattern="^(raw_vs_processed|processed_vs_corrected)$"
    ),
    user_id: str | None = Query(None),
    limit: int = Query(100, le=500),
    _current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Any]:
    """Accuracy history.
    
    Args:
        mode (str | None): The mode.
        accuracy_type (str | None): The accuracy type.
        user_id (str | None): Unique identifier of the user.
        limit (int): Limit integer.
        _current_user (User): The  current user.
        db (Session): Database session.
    
    Returns:
        list[Any]: List of Any.
    """
    return LogRepository.get_accuracy_logs(
        db,
        mode=mode,
        accuracy_type=accuracy_type,
        user_id=user_id,
        limit=limit,
    )
