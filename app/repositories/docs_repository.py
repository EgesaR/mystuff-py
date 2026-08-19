"""Docs page repository handling database queries for DocPage models."""
from sqlalchemy.orm import Session

from app.models.doc_page import DocPage
from app.repositories.base_repository import BaseRepository


class DocsRepository(BaseRepository[DocPage]):
    """Repository class for executing database operations on DocPage records."""

    model: type[DocPage] = DocPage

    @classmethod
    def get_by_slug(cls, db: Session, slug: str) -> DocPage | None:
        """Retrieve a single docs page by its slug.

        Args:
            db (Session): Database session.
            slug (str): URL-safe slug identifying the page.

        Returns:
            DocPage | None: Matching page, if any.
        """
        return db.query(cls.model).filter(cls.model.slug == slug).first()

    @classmethod
    def get_all_ordered(cls, db: Session) -> list[DocPage]:
        """Retrieve every docs page ordered by category, then manual order.

        Args:
            db (Session): Database session.

        Returns:
            list[DocPage]: List of docs pages.
        """
        return (
            db.query(cls.model)
            .order_by(cls.model.category.asc(), cls.model.order.asc())
            .all()
        )
