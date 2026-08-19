"""Docs service module managing business logic operations for documentation pages."""
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.slugify import slugify
from app.models.doc_page import DocPage
from app.repositories.docs_repository import DocsRepository


class DocsService:
    """Business logic for creating and reading documentation pages."""

    @staticmethod
    def _unique_slug(db: Session, title: str) -> str:
        """Generate a slug for a title, disambiguating collisions with a numeric suffix.

        Args:
            db (Session): Database session.
            title (str): Page title to derive the slug from.

        Returns:
            str: A slug guaranteed to be unique in the doc_pages table.
        """
        base = slugify(title)
        slug = base
        suffix = 2
        while DocsRepository.get_by_slug(db, slug) is not None:
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    @staticmethod
    def create_page(db: Session, title: str, category: str, content: str, order: int) -> DocPage:
        """Create a new docs page. Developer-only.

        Args:
            db (Session): Database session.
            title (str): Page title.
            category (str): Sidebar grouping, e.g. "Getting Started".
            content (str): Markdown page body.
            order (int): Manual sort order within the category.

        Returns:
            DocPage: The created page.
        """
        return DocsRepository.create(
            db,
            obj_in={
                "slug": DocsService._unique_slug(db, title),
                "title": title,
                "category": category,
                "content": content,
                "order": order,
            },
        )

    @staticmethod
    def update_page(db: Session, page_id: str, **fields: object) -> DocPage:
        """Update a docs page. Developer-only.

        Args:
            db (Session): Database session.
            page_id (str): Unique identifier of the page.
            **fields: Any subset of updatable DocPage fields (None values are ignored).

        Returns:
            DocPage: The updated page.
        """
        page = DocsRepository.get(db, page_id)
        if not page:
            raise NotFoundError("Docs page not found")
        update_data = {k: v for k, v in fields.items() if v is not None}
        return DocsRepository.update(db, db_obj=page, update_data=update_data)

    @staticmethod
    def list_all(db: Session) -> list[DocPage]:
        """List every docs page, ordered by category then manual order."""
        return DocsRepository.get_all_ordered(db)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> DocPage:
        """Fetch a single docs page by slug.

        Args:
            db (Session): Database session.
            slug (str): Page slug.

        Returns:
            DocPage: The matching page.
        """
        page = DocsRepository.get_by_slug(db, slug)
        if not page:
            raise NotFoundError("Docs page not found")
        return page

    @staticmethod
    def get_by_id(db: Session, page_id: str) -> DocPage:
        """Fetch a single docs page by id. Developer-only (used by the admin editor).
 
        Args:
            db (Session): Database session.
            page_id (str): Unique identifier of the page.
 
        Returns:
            DocPage: The matching page.
        """
        page = DocsRepository.get(db, page_id)
        if not page:
            raise NotFoundError("Docs page not found")
        return page
