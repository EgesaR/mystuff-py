"""User repository for database operations on User entities."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository class for CRUD operations on User models."""

    model = User

    @classmethod
    def get_by_email(cls, db: Session, email: str) -> User | None:
        """Retrieve a user by their email address."""
        return db.query(cls.model).filter(cls.model.email == email).first()

    @classmethod
    def get_by_username(cls, db: Session, username: str) -> User | None:
        """Retrieve a user by their username."""
        return db.query(cls.model).filter(cls.model.username == username).first()

    @classmethod
    def create_user(
        cls,
        db: Session,
        *,
        email: str,
        username: str,
        hashed_password: str,
        full_name: str | None = None,
    ) -> User:
        """Create and persist a new user record."""
        user = cls.model(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except Exception:
            db.rollback()
            raise
