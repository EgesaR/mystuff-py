from fastapi import (
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketException,
    status,
)
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User


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


def get_token_from_ws_cookie(websocket: WebSocket) -> str:
    """Retrieve the access token from the WebSocket handshake cookie."""

    token = websocket.cookies.get("access_token")

    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated: missing access_token cookie",
        )

    return token


def get_current_user_ws(
    token: str = Depends(get_token_from_ws_cookie),
    db: Session = Depends(get_db),
) -> User:
    """Retrieve the currently authenticated WebSocket user."""

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
