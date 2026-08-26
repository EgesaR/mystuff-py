"""Blog listing, reading, and developer authoring endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_developer
from app.api.deps.database import get_db
from app.core.errors import NotFoundError
from app.models.blog_post import BlogPost
from app.models.user import User
from app.schemas.blog import (
    BlogPostCreate,
    BlogPostResponse,
    BlogPostSummary,
    BlogPostUpdate,
)
from app.services.blog_service import BlogService

logger = logging.getLogger("app")

router = APIRouter()


@router.get(
    "",
    response_model=list[BlogPostSummary],
    summary="List published blog posts",
)
def list_posts(
    db: Session = Depends(get_db),
) -> list[BlogPost]:
    """List every published blog post, newest first."""
    return BlogService.list_published(db)


# Keep this before GET /{slug} so "admin" is not treated as a slug.
@router.get(
    "/admin",
    response_model=list[BlogPostSummary],
    summary="List every blog post including drafts (developer only)",
)
def list_all_posts(
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> list[BlogPost]:
    """List every blog post regardless of publish status."""
    return BlogService.list_all(db)


@router.get(
    "/admin/{post_id}",
    response_model=BlogPostResponse,
    summary="Get a single blog post by id, including drafts (developer only)",
)
def get_post_admin(
    post_id: str,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> BlogPost:
    """Fetch a single post by id regardless of publish status."""
    try:
        return BlogService.get_by_id(db, post_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        ) from exc


@router.get(
    "/{slug}",
    response_model=BlogPostResponse,
    summary="Get a blog post by slug",
)
def get_post(
    slug: str,
    db: Session = Depends(get_db),
) -> BlogPost:
    """Fetch a single published blog post by slug."""
    try:
        return BlogService.get_by_slug(db, slug)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        ) from exc


@router.post(
    "",
    response_model=BlogPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a blog post (developer only)",
)
def create_post(
    payload: BlogPostCreate,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> BlogPost:
    """Create a new blog post."""
    return BlogService.create_post(
        db,
        author_id=current_user.id,
        title=payload.title,
        excerpt=payload.excerpt,
        content=payload.content,
        cover_image_url=payload.cover_image_url,
        tags=payload.tags,
        is_published=payload.is_published,
    )


@router.patch(
    "/{post_id}",
    response_model=BlogPostResponse,
    summary="Update a blog post (developer only)",
)
def update_post(
    post_id: str,
    payload: BlogPostUpdate,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> BlogPost:
    """Update or publish a blog post."""
    try:
        return BlogService.update_post(
            db,
            post_id,
            payload,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        ) from exc
