from sqlalchemy.orm import Session

from app.models.enums import ShareResourceType
from app.models.share import Share
from app.repositories.base_repository import BaseRepository


class ShareRepository(BaseRepository[Share]):
    model = Share

    @classmethod
    def get_by_token(cls, db: Session, token: str) -> Share | None:
        return db.query(cls.model).filter(cls.model.token == token).first()

    @classmethod
    def get_incoming(cls, db: Session, user_id: str) -> list[Share]:
        return (
            db.query(cls.model)
            .filter(cls.model.target_user_id == user_id)
            .order_by(cls.model.created_at.desc())
            .all()
        )

    @classmethod
    def get_for_resource(
        cls,
        db: Session,
        resource_type: ShareResourceType,
        resource_id: str,
        owner_id: str
    ) -> list[Share]:
        return (
            db.query(cls.model)
            .filter(
                cls.model.resource_type == resource_type,
                cls.model.resource_id == resource_id,
                cls.model.owner_id == owner_id
            ).all()
        )

    @classmethod
    def get_accepted_for_resource(
        cls, db: Session, resource_type: ShareResourceType, resource_id: str, user_id: str
    ) -> Share | None:
        return (
            db.query(cls.model)
            .filter(
                cls.model.resource_type == resource_type,
                cls.model.resource_id == resource_id,
                cls.model.target_user_id == user_id,
                cls.model.status == "accepted"
            ).first()
        )
