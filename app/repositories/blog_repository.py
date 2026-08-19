"""Blog post repository handling database queries for BlogPost models."""
from sqlalchemy.orm import Session, joinedload

from app.models.blog_post import BlogPost
from app.repositories.base_repository import BaseRepository


class BlogRepository(BaseRepository[BlogPost]):
    """Repository class for executing database operations on BlogPost records."""

    model: type[BlogPost] = BlogPost

    @classmethod
    def get_by_slug(cls, db: Session, slug: str) -> BlogPost | None:
        """Retrieve a single blog post by its slug, with the author eager-loaded.

        Args:
            db (Session): Database session.
            slug (str): URL-safe slug identifying the post.

        Returns:
            BlogPost | None: Matching post, if any.
        """
        return (
            db.query(cls.model)
            .options(joinedload(cls.model.author))
            .filter(cls.model.slug == slug)
            .first()
        )

    @classmethod
    def get_published(cls, db: Session) -> list[BlogPost]:
        """Retrieve every published post, newest first.

        Args:
            db (Session): Database session.

        Returns:
            list[BlogPost]: List of published posts.
        """
        return (
            db.query(cls.model)
            .options(joinedload(cls.model.author))
            .filter(cls.model.is_published.is_(True))
            .order_by(cls.model.published_at.desc())
            .all()
        )

    @classmethod
    def get_all_with_author(cls, db: Session) -> list[BlogPost]:
        """Retrieve every post regardless of publish status, author eager-loaded.

        Args:
            db (Session): Database session.

        Returns:
            list[BlogPost]: List of all posts, newest first.
        """
        return (
            db.query(cls.model)
            .options(joinedload(cls.model.author))
            .order_by(cls.model.created_at.desc())
            .all()
        )
