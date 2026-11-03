"""Repository for persisted per-user workspace state."""

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.workspace import WorkspaceState
from app.repositories.base_repository import BaseRepository


class WorkspaceRepository(BaseRepository[WorkspaceState]):
    """Database operations for user workspace state."""

    model: type[WorkspaceState] = WorkspaceState

    @classmethod
    def get_by_user(
        cls,
        db: Session,
        user_id: UUID,
    ) -> WorkspaceState | None:
        """Retrieve workspace state belonging to a specific user.

        Args:
            db: Active database session.
            user_id: UUID of the workspace owner.

        Returns:
            The user's workspace state, or None if no record exists.
        """
        return db.query(cls.model).filter(cls.model.user_id == user_id).first()

    @classmethod
    def upsert_state(
        cls,
        db: Session,
        user_id: UUID,
        data: dict[str, Any],
    ) -> WorkspaceState:
        """Create or update a user's persisted workspace state.

        Handles concurrent first-time synchronization requests by recovering
        from a unique user_id constraint violation and updating the record
        created by the winning request.

        Args:
            db: Active database session.
            user_id: UUID of the workspace owner.
            data: Workspace state payload.

        Returns:
            The persisted workspace state.

        Raises:
            IntegrityError: If persistence fails due to a database constraint.
            Exception: If another database operation fails.
        """
        record = cls.get_by_user(db, user_id)
        creating = record is None

        try:
            if record is None:
                record = cls.model(
                    user_id=user_id,
                    state_data=data,
                )
                db.add(record)
            else:
                record.state_data = data

            try:
                db.commit()

            except IntegrityError:
                db.rollback()

                # Only recover from a concurrent first-time insertion.
                if not creating:
                    raise

                record = cls.get_by_user(db, user_id)

                if record is None:
                    raise

                record.state_data = data
                db.commit()

            db.refresh(record)
            return record

        except Exception:
            db.rollback()
            raise
