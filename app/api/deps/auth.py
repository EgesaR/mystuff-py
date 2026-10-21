import logging

from fastapi import (
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketException,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User

logger = logging.getLogger("app")


# ──────────────────────────────────────────────────────────────
# HTTP Auth
# ──────────────────────────────────────────────────────────────

def get_token_from_cookie(request: Request) -> str:
    """Retrieve the access token from the HTTP cookie."""
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: missing access_token cookie",
        )

    return token


def get_current_user(
    token: str = Depends(get_token_from_cookie),
    db: Session = Depends(get_db),
) -> User:
    """Retrieve the currently authenticated HTTP user."""
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == payload.sub).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def require_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the authenticated user to be active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_developer(
    current_user: User = Depends(require_active_user),
) -> User:
    """Require the current user to have developer privileges."""
    if not getattr(current_user, "is_developer", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer access required",
        )
    return current_user


def require_admin(
    current_user: User = Depends(require_active_user),
) -> User:
    """Require administrator privileges."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user


# ──────────────────────────────────────────────────────────────
# WebSocket Auth
# ──────────────────────────────────────────────────────────────

def get_current_user_ws(
    websocket: WebSocket,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Retrieve the currently authenticated WebSocket user.

    Token is taken from:
    1. Query parameter  (?token=...)   ← needed for production (cross-origin)
    2. Cookie           (access_token) ← works in local development
    """
    if not token:
        token = websocket.cookies.get("access_token")

    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated",
        )

    payload = decode_access_token(token)

    if payload is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == payload.sub).first()

    if user is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User not found",
        )

    if not user.is_active:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Inactive user",
        )

    logger.info(
        "WS auth – user=%s is_developer=%s",
        user.id,
        getattr(user, "is_developer", False),
    )

    return user


def get_current_user_ws_cookie(
    websocket: WebSocket,
    db: Session = Depends(get_db),
) -> User:
    """Authenticate a WebSocket using an allowed Origin and the auth cookie."""
    origin = websocket.headers.get("origin")
    if origin not in settings.ALLOWED_ORIGINS:
        logger.warning(
            "Sync WebSocket rejected: reason=origin_not_allowed origin=%s",
            origin[:256] if origin else None,
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Origin not allowed",
        )

    token = websocket.cookies.get("access_token")
    if not token:
        logger.warning(
            "Sync WebSocket rejected: reason=missing_access_token origin=%s",
            origin,
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated",
        )

    payload = decode_access_token(token)
    if payload is None:
        logger.warning(
            "Sync WebSocket rejected: reason=invalid_access_token origin=%s",
            origin,
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == payload.sub).first()
    if user is None or not user.is_active:
        logger.warning(
            "Sync WebSocket rejected: reason=user_unavailable origin=%s",
            origin,
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User is unavailable",
        )
    return user


def require_developer_ws(
    current_user: User = Depends(get_current_user_ws),
) -> User:
    """Require developer privileges for WebSocket connections."""
    if not getattr(current_user, "is_developer", False):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Developer access required",
        )
    return current_user
