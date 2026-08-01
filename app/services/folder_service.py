"""app/services/folder_service.py

Folder business logic controller processing tree hierarchies and metadata.

Access model: ownership always grants full access. A non-owner gets in only
via an *accepted* Share row for that folder — VIEW is enough to read
(list_folders, get_folder_tree), but update/delete require EDIT.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import SharePermission, ShareResourceType, ShareStatus
from app.repositories.folder_repository import FolderRepository
from app.repositories.share_repository import ShareRepository


class FolderService:
    """Manages lifecycle and hierarchical operations for directory folders."""

    @staticmethod
    def _get_accessible_folder(
        db: Session, folder_id: str, user_id: str, *, require_edit: bool = False
    ) -> Any:
        """Fetch a folder the user owns or has an accepted share for.

        Args:
            db (Session): Database session.
            folder_id (str): Unique identifier of the folder.
            user_id (str): Unique identifier of the user.
            require_edit (bool): If True, a non-owner must hold
                SharePermission.EDIT rather than just VIEW.

        Returns:
            Any: The Folder row.
        """
        folder = FolderRepository.get(db, folder_id)
        if not folder:
            raise NotFoundError("Folder not found")

        if folder.owner_id == user_id:
            return folder

        share = ShareRepository.get_accepted_for_resource(
            db, ShareResourceType.FOLDER, folder_id, user_id
        )
        if share is None:
            raise PermissionDeniedError("Access denied")
        if require_edit and share.permission != SharePermission.EDIT:
            raise PermissionDeniedError("View-only access")

        return folder

    @staticmethod
    def create_folder(
        db: Session,
        user_id: str,
        name: str,
        color: str | None = None,
        parent_id: str | None = None,
    ) -> Any:
        """Create folder."""
        existing = FolderRepository.get_folder_by_name(
            db, name, user_id, parent_id
        )
        if existing:
            raise ValueError("Folder already exists")
        return FolderRepository.create(
            db,
            {
                "name": name,
                "owner_id": user_id,
                "parent_id": parent_id,
                "color": color,
            },
        )

    @staticmethod
    def list_folders(
        db: Session, user_id: str, parent_id: str | None = None
    ) -> list[Any]:
        """List folders owned by the user."""
        return FolderRepository.get_folders(
            db, user_id=user_id, parent_id=parent_id
        )

    @staticmethod
    def list_shared_folders(db: Session, user_id: str) -> list[Any]:
        """List folders shared with the user (accepted invites only)."""
        shares = [
            s for s in ShareRepository.get_incoming(db, user_id)
            if s.resource_type == ShareResourceType.FOLDER
            and s.status == ShareStatus.ACCEPTED
        ]
        folders = [FolderRepository.get(db, s.resource_id) for s in shares]
        return [f for f in folders if f is not None]

    @staticmethod
    def update_folder(
        db: Session, folder_id: str, user_id: str, data: dict[str, Any]
    ) -> Any:
        """Update folder. Requires ownership or an EDIT share."""
        folder = FolderService._get_accessible_folder(
            db, folder_id, user_id, require_edit=True
        )
        return FolderRepository.update(
            db, db_obj=folder, update_data=data
        )

    @staticmethod
    def delete_folder(db: Session, folder_id: str, user_id: str) -> None:
        """Delete folder. Requires ownership or an EDIT share."""
        folder = FolderService._get_accessible_folder(
            db, folder_id, user_id, require_edit=True
        )
        FolderRepository.delete(db, db_obj=folder)

    @staticmethod
    def get_user_folders(db: Session, user_id: str) -> list[Any]:
        """Retrieve all folders belonging to a user."""
        return FolderRepository.get_user_folders(db, user_id)

    @staticmethod
    def get_folder_tree(db: Session, folder_id: str, user_id: str) -> Any:
        """Retrieve a folder with its full nested children tree.

        Access via ownership or an accepted (VIEW or EDIT) share.
        """
        folder = FolderService._get_accessible_folder(db, folder_id, user_id)
        folder.children = FolderService._build_children(db, folder.id)
        return folder

    @staticmethod
    def _build_children(db: Session, parent_id: str) -> list[Any]:
        """Recursively attach nested children to every folder in the subtree.

        Args:
            db (Session): Database session.
            parent_id (str): Unique identifier of the parent folder.

        Returns:
            list[Any]: Child Folder rows, each carrying its own .children.
        """
        children = FolderRepository.get_by_parent(db, parent_id)
        for child in children:
            child.children = FolderService._build_children(db, child.id)
        return children
