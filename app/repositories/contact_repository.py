"""Contact message repository handling database queries for ContactMessage models."""

from sqlalchemy.orm import Session

from app.models.contact_messages import ContactMessage
from app.repositories.base_repository import BaseRepository


class ContactRepository(BaseRepository[ContactMessage]):
    """Repository class for executing database operations on ContactMessage records."""

    model: type[ContactMessage] = ContactMessage

    @classmethod
    def get_all(
        cls,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ContactMessage]:
        """Retrieve contact submissions, newest first.

        Args:
            db: Database session.
            skip: Number of submissions to skip.
            limit: Maximum number of submissions to return.

        Returns:
            List of contact submissions.
        """
        return (
            db.query(cls.model)
            .order_by(cls.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
