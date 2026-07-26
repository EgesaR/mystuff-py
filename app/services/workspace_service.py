"""Business logic for workspace state synchronization."""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.workspace_repository import WorkspaceRepository


class WorkspaceService:

    @staticmethod
    def get_state(db: Session, user_id: str) -> dict[str, Any] | None:
        """Retrieve state.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            dict[str, Any] | None: Response payload or None.
        """
        record = WorkspaceRepository.get_by_user(db, user_id)
        if not record:
            return None

        return {
            "state_data": record.state_data,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None
        }

    @staticmethod
    def sync_state(db: Session, user_id: str, state_data: dict[str, Any]) -> dict[str, Any]:
        """Sync state.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            state_data (dict[str, Any]): The state data.
        
        Returns:
            dict[str, Any]: Response payload.
        """
        record = WorkspaceRepository.upsert_state(db, user_id, state_data)
        return {
            "state_data": record.state_data,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None
        }
