"""Docs listing, reading, and developer authoring endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_developer
from app.api.deps.database import get_db
from app.core.errors import NotFoundError
from app.models.doc_page import DocPage
from app.models.user import User
from app.schemas.docs import DocPageCreate, DocPageResponse, DocPageSummary, DocPageUpdate
from app.services.docs_service import DocsService

logger = logging.getLogger("app")
router = APIRouter()


@router.get("", response_model=list[DocPageSummary], summary="List all docs pages")
def list_pages(db: Session = Depends(get_db)) -> list[DocPage]:
    """List every docs page, ordered by category then manual order.

    Args:
        db (Session): Database session.

    Returns:
        list[DocPage]: Docs pages.
    """
    return DocsService.list_all(db)


router.get(
    "/admin/{page_id}",
    response_model=DocPageResponse,
    summary="Get a single docs page by id (developer only)",
)


def get_page_admin(
    page_id: str,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> DocPage:
    """Fetch a single docs page by id. Used by the admin editor."""
    try:
        return DocsService.get_by_id(db, page_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Docs page not found"
        ) from exc


@router.get("/{slug}", response_model=DocPageResponse, summary="Get a docs page by slug")
def get_page(slug: str, db: Session = Depends(get_db)) -> DocPage:
    """Fetch a single docs page by its slug.

    Args:
        slug (str): URL-safe page slug.
        db (Session): Database session.

    Returns:
        DocPage: The matching page.
    """
    try:
        return DocsService.get_by_slug(db, slug)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Docs page not found"
        ) from exc


@router.post(
    "",
    response_model=DocPageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a docs page (developer only)",
)
def create_page(
    payload: DocPageCreate,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> DocPage:
    """Create a new docs page. Requires developer access."""
    return DocsService.create_page(
        db,
        title=payload.title,
        category=payload.category,
        content=payload.content,
        order=payload.order,
    )


@router.patch(
    "/{page_id}",
    response_model=DocPageResponse,
    summary="Update a docs page (developer only)",
)
def update_page(
    page_id: str,
    payload: DocPageUpdate,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> DocPage:
    """Update a docs page. Requires developer access."""
    try:
        return DocsService.update_page(db, page_id, **payload.model_dump())
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Docs page not found"
        ) from exc
