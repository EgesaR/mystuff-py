"""User repository for database operations on User entities."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository class for CRUD operations on User models."""

    model = User

    @classmethod
    def get_by_email(cls, db: Session, email: str) -> User | None:
        """Retrieve by email.
        
        Args:
            db (Session): Database session.
            email (str): Email address.
        
        Returns:
            User | None: User data.
        """
        return db.query(cls.model).filter(cls.model.email == email).first()

    @classmethod
    def get_by_username(cls, db: Session, username: str) -> User | None:
        """Retrieve by username.
        
        Args:
            db (Session): Database session.
            username (str): Username.
        
        Returns:
            User | None: User data.
        """
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
        """Create user.
        
        Args:
            db (Session): Database session.
            email (str): Email address.
            username (str): Username.
            hashed_password (str): Hashed password string.
            full_name (str | None): User full name.
        
        Returns:
            User: User data.
        """
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
