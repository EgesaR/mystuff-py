"""Blog service module managing business logic operations for blog posts."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.slugify import slugify
from app.models.blog_post import BlogPost
from app.repositories.blog_repository import BlogRepository
from app.schemas.blog import BlogPostUpdate


class BlogService:
    """Business logic for creating, publishing, and reading blog posts."""

    @staticmethod
    def _unique_slug(db: Session, title: str) -> str:
        """Generate a unique slug for a title, disambiguating collisions with a numeric suffix.
        
        Args:
            db: (Session): Database session.
            title: (str): Post title to derive the slug form.
            
        Returns:
            str: A slug guaranteed to be unique in the blog_posts table
        """
        base = slugify(title)
        slug = base
        suffix = 2

        while BlogRepository.get_by_slug(db, slug) is not None:
            slug = f"{base}-{suffix}"
            suffix += 1

        return slug

    @staticmethod
    def create_post(
        db: Session,
        author_id: str,
        title: str,
        excerpt: str,
        content: str,
        cover_image_url: str | None,
        tags: list[str],
        is_published: bool,
    ) -> BlogPost:
        """Create a new blog post. Developer-only.
 
        Args:
            db (Session): Database session.
            author_id (str): Unique identifier of the authoring user.
            title (str): Post title.
            excerpt (str): Short summary shown in listings and meta descriptions.
            content (str): Markdown post body.
            cover_image_url (str | None): Optional cover image URL.
            tags (list[str]): Post tags.
            is_published (bool): Whether the post is published immediately.
 
        Returns:
            BlogPost: The created post, with the author eager-loaded.
        """
        post = BlogRepository.create(
            db,
            obj_in={
                "slug": BlogService._unique_slug(db, title),
                "title": title,
                "excerpt": excerpt,
                "content": content,
                "cover_image_url": cover_image_url,
                "tags": ",".join(tags),
                "is_published": is_published,
                "published_at": datetime.now(UTC) if is_published else None,
                "author_id": author_id,
            },
        )

        created_post = BlogRepository.get_by_slug(db, post.slug)

        if created_post is None:
            raise NotFoundError("Created blog post could not be retrieved")

        return created_post

    @staticmethod
    def update_post(
        db: Session,
        post_id: str,
        update: BlogPostUpdate,
    ) -> BlogPost:
        """Update a blog post, stamping `published_at` the moment it's first published.
 
        Args:
            db (Session): Database session.
            post_id (str): Unique identifier of the post.
            **fields: Any subset of updatable BlogPost fields (None values are ignored).
 
        Returns:
            BlogPost: The updated post.
        """

        post = BlogRepository.get(db, post_id)

        if post is None:
            raise NotFoundError("Blog post not found")

        update_data = update.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        if update.tags is not None:
            update_data["tags"] = ",".join(update.tags)

        if update.is_published and not post.is_published:
            update_data["published_at"] = datetime.now(UTC)

        return BlogRepository.update(
            db,
            db_obj=post,
            update_data=update_data,
        )

    @staticmethod
    def list_published(db: Session) -> list[BlogPost]:
        """List every published post, newest first."""
        return BlogRepository.get_published(db)

    @staticmethod
    def list_all(db: Session) -> list[BlogPost]:
        """List every post regardless of status. Developer-only."""
        return BlogRepository.get_all_with_author(db)

    @staticmethod
    def get_by_slug(
        db: Session,
        slug: str,
        *,
        include_unpublished: bool = False,
    ) -> BlogPost:
        """Fetch a single post by slug.
 
        Args:
            db (Session): Database session.
            slug (str): Post slug.
            include_unpublished (bool): Whether drafts are visible (developer views).
 
        Returns:
            BlogPost: The matching post.
        """
        post = BlogRepository.get_by_slug(db, slug)
        if not post or (not post.is_published and not include_unpublished):
            raise NotFoundError("Blog post not found")
        return post
    
    @staticmethod
    def get_by_id(db: Session, post_id: str) -> BlogPost:
        """Fetch a single post by id, including drafts. Developer-only (used by the admin editor).
 
        Args:
            db (Session): Database session.
            post_id (str): Unique identifier of the post.
 
        Returns:
            BlogPost: The matching post, with the author eager-loaded.
        """
        post = BlogRepository.get(db, post_id)
        if post is None:
            raise NotFoundError("Blog post not found")
        post_with_author =  BlogRepository.get_by_slug(db, post.slug)
        
        if post_with_author is None:
            raise NotFoundError("Blog post not found")

        return post_with_author