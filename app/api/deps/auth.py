from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User


def get_token_from_cookie(request: Request) -> str:
    """Retrieve token from cookie.

    Args:
        request (Request): Incoming HTTP request.

    Returns:
        str: Processed string result.
    """
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
    """Retrieve current user.

    Args:
        token (str): Token string.
        db (Session): Database session.

    Returns:
        User: User data.
    """
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
    """Require active user.

    Args:
        current_user (User): Authenticated user performing the action.

    Returns:
        User: User data.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_developer(
    current_user: User = Depends(require_active_user),
) -> User:
    """Require the current user to have developer privileges.

    Args:
        current_user (User): Authenticated user performing the action.

    Returns:
        User: User result.
    """
    if not getattr(current_user, "is_developer", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer access required",
        )
    return current_user


def get_token_from_ws_cookie(websocket: WebSocket) -> str:
    """Retrieve token from websocket cookie."""
    token = websocket.cookies.get("access_token")
    if not token:
        # WebSockets must use WebSocketException, not HTTPException
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated: missing access_token cookie"
        )
    return token


def get_current_user_ws(
    websocket: WebSocket,
    token: str = Depends(get_token_from_ws_cookie),
    db: Session = Depends(get_db)
) -> User:
    """Retrieve current user for WebSocket connections."""
    payload = decode_access_token(token)

    if payload is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token"
        )

    user = db.query(User).filter(User.id == payload.sub).first()

    if user is None or not user.is_active:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User not found or inactive"
        )

    return user
