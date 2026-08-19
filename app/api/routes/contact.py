"""Public contact-form submission and developer inbox endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_developer
from app.api.deps.database import get_db
from app.core.errors import NotFoundError
from app.models.contact_messages import ContactMessage
from app.models.user import User
from app.schemas.contact import ContactMessageCreate, ContactMessageResponse
from app.services.contact_service import ContactService

logger = logging.getLogger("app")
router = APIRouter()


@router.post(
    "",
    response_model=ContactMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit the public contact form",
)
def submit_contact_message(payload: ContactMessageCreate, db: Session = Depends(get_db)) -> ContactMessage:
    """Submit a message from the public contact form. No authentication required.

    Args:
        payload (ContactMessageCreate): Request payload.
        db (Session): Database session.

    Returns:
        ContactMessage: The created message.
    """
    logger.info("Contact form submission from: %s", payload.email)
    return ContactService.submit_message(
        db,
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
    )


@router.get(
    "",
    response_model=list[ContactMessageResponse],
    summary="List contact submissions (developer only)",
)
def list_contact_messages(
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> list[ContactMessage]:
    """List every contact form submission. Requires developer access."""
    return ContactService.list_messages(db)


@router.patch(
    "/{message_id}/read",
    response_model=ContactMessageResponse,
    summary="Mark a contact message as read (developer only)",
)
def mark_message_read(
    message_id: str,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> ContactMessage:
    """Mark a contact submission as read. Requires developer access."""
    try:
        return ContactService.mark_read(db, message_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact message not found"
        ) from exc
