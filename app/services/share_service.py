from datetime import timedelta

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.security import create_share_token, decode_share_token
from app.models.enums import NotificationType, SharePermission, ShareResourceType, ShareStatus
from app.repositories.share_repository import ShareRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService


class ShareService:

    @staticmethod
    def create_share(
        db: Session, *, owner_id: str, resource_type: ShareResourceType,
        resource_id: str, target_username: str, permission: SharePermission,
        background_tasks: BackgroundTasks
    ):
        target = UserRepository.get_by_username(db, target_username)
        if not target:
            raise NotFoundError("User not found")

        token = create_share_token(
            owner_id=owner_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission.value,
            target_user_id=target.id,
            expires_delta=timedelta(days=14),
        )

        share = ShareRepository.create(
            db,
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "owner_id": owner_id,
                "target_user_id": target.id,
                "permission": permission,
                "status": ShareStatus.PENDING,
                "token": token
            }
        )

        NotificationService.create(
            db=db,
            recipient_id=target.id,
            sender_id=owner_id,
            title="New share invite",
            message=f"You've been invited to a shared {resource_type.value}.",
            notification_type=NotificationType.SHARE_INVITE,
            link=f"/shared/accept/{token}",
            background_tasks=background_tasks
        )

        return share

    @staticmethod
    def accept_share(db: Session, *, token: str, user_id: str):
        payload = decode_share_token(token)
        if payload is None:
            raise NotFoundError("Invalid or expired share link")

        share = ShareRepository.get_by_token(db, token)
        if share is None:
            raise NotFoundError("Share not found")

        if share.target_user_id != user_id or payload.get("target") != user_id:
            raise PermissionDeniedError("This share was not issued to you")

        return ShareRepository.update(
            db, db_obj=share, update_data={"status": ShareStatus.ACCEPTED}
        )

    @staticmethod
    def list_incoming(db: Session, user_id: str):
        return ShareRepository.get_incoming(db, user_id)

    @staticmethod
    def list_for_resource(db: Session, resource_type: ShareResourceType, resource_id: str, owner_id: str):
        return ShareRepository.get_for_resource(db, resource_type, resource_id, owner_id)

    @staticmethod
    def has_access(db: Session, resource_type: ShareResourceType, resource_id: str, user_id: str) -> bool:
        return ShareRepository.get_accepted_for_resource(db, resource_type, resource_id, user_id) is not None
