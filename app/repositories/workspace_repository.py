"""Repository for workspace state persistence."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.workspace import WorkspaceState
from app.repositories.base_repository import BaseRepository


class WorkspaceRepository(BaseRepository[WorkspaceState]):
    model = WorkspaceState

    @classmethod
    def get_by_user(cls, db: Session, user_id: str) -> WorkspaceState | None:
        """Retrieve by user.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            WorkspaceState | None: WorkspaceState or None.
        """
        return db.query(cls.model).filter(cls.model.user_id == user_id).first()

    @classmethod
    def upsert_state(cls, db: Session, user_id: str, data: dict[str, Any]) -> WorkspaceState:
        """Upsert state.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            data (dict[str, Any]): The data.
        
        Returns:
            WorkspaceState: WorkspaceState result.
        """
        record = cls.get_by_user(db, user_id)

        if record:
            record.state_data = data
        else:
            record = cls.model(user_id=user_id, state_data=data)
            db.add(record)

        db.commit()
        db.refresh(record)
        return record
