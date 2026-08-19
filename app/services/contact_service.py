"""Contact service module handling public contact-form submissions."""
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.contact_messages import ContactMessage
from app.repositories.contact_repository import ContactRepository


class ContactService:
    """Business logic for the public contact form and its developer inbox."""

    @staticmethod
    def submit_message(db: Session, name: str, email: str, subject: str, message: str) -> ContactMessage:
        """Persist a new contact form submission.

        Args:
            db (Session): Database session.
            name (str): Sender's name.
            email (str): Sender's email address.
            subject (str): Message subject line.
            message (str): Message body.

        Returns:
            ContactMessage: The created message.
        """
        return ContactRepository.create(
            db,
            obj_in={"name": name, "email": email,
                    "subject": subject, "message": message},
        )

    @staticmethod
    def list_messages(db: Session) -> list[ContactMessage]:
        """List every contact submission, newest first. Developer-only."""
        return ContactRepository.get_all(db)

    @staticmethod
    def mark_read(db: Session, message_id: str) -> ContactMessage:
        """Mark a contact message as read. Developer-only.

        Args:
            db (Session): Database session.
            message_id (str): Unique identifier of the message.

        Returns:
            ContactMessage: The updated message.
        """
        message = ContactRepository.get(db, message_id)
        if not message:
            raise NotFoundError("Contact message not found")
        return ContactRepository.update(db, db_obj=message, update_data={"is_read": True})
