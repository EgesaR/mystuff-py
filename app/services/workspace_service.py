"""Business logic for workspace state synchronization."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceStatePayload


class WorkspaceService:
    @staticmethod
    def get_state(db: Session, user_id: UUID) -> dict[str, Any] | None:
        """Retrieve state.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.

        Returns:
            dict[str, Any] | None: Response payload or None.
        """
        record = WorkspaceRepository.get_by_user(db, user_id)
        if record is None:
            return {"state_data": None, "updated_at": None}

        return {"state_data": record.state_data, "updated_at": record.updated_at.isoformat() if record.updated_at else None}

    @staticmethod
    def sync_state(db: Session, user_id: UUID, payload: WorkspaceStatePayload) -> dict[str, Any]:
        """Sync state.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            state_data (dict[str, Any]): The state data.

        Returns:
            dict[str, Any]: Response payload.
        """
        normalized_state = payload.model_dump(mode="json", by_alias=True)
        record = WorkspaceRepository.upsert_state(db, user_id, normalized_state)
        return {"state_data": record.state_data, "updated_at": record.updated_at.isoformat() if record.updated_at else None}
