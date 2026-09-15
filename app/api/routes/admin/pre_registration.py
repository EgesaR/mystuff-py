from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

# Replace this import with the dependency that already
# exists in your authentication system.
from app.api.deps.auth import require_admin
from app.core.config import settings
from app.database.session import SessionLocal, get_db
from app.models.pre_registration import PreRegistration
from app.schemas.pre_registration import (
    AdminPreRegistrationListResponse,
    LaunchEmailRequest,
    LaunchEmailResponse,
    PreRegistrationResponse,
)
from app.services.email_service import EmailService
from app.services.pre_registration_service import (
    PreRegistrationService,
)

# SQLAlchemy's dynamic `func` API is intentionally difficult
# for Pylint to infer correctly.
# pylint: disable=not-callable


router = APIRouter(
    prefix="/api/admin/pre-registrations",
    tags=["Admin Pre-registration"],
    dependencies=[
        Depends(require_admin),
    ],
)


@router.get(
    "",
    response_model=AdminPreRegistrationListResponse,
)
def list_pre_registrations(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    search: str | None = Query(
        default=None,
    ),
    status: str = Query(
        default="all",
    ),
    db: Session = Depends(get_db),
) -> AdminPreRegistrationListResponse:
    """Return paginated pre-registration records and statistics."""
    query = select(PreRegistration)

    if search:
        pattern = (
            f"%{search.strip().lower()}%"
        )

        query = query.where(
            or_(
                func.lower(
                    PreRegistration.email
                ).like(pattern),
                func.lower(
                    func.coalesce(
                        PreRegistration.name,
                        "",
                    )
                ).like(pattern),
            )
        )

    if status == "verified":
        query = query.where(
            PreRegistration.verified.is_(True)
        )

    elif status == "unverified":
        query = query.where(
            PreRegistration.verified.is_(False)
        )

    elif status == "subscribed":
        query = query.where(
            PreRegistration.subscribed.is_(True)
        )

    elif status == "unsubscribed":
        query = query.where(
            PreRegistration.subscribed.is_(False)
        )

    elif status != "all":
        raise HTTPException(
            status_code=400,
            detail="Invalid pre-registration status.",
        )

    total = (
        db.scalar(
            select(func.count())
            .select_from(query.subquery())
        )
        or 0
    )

    records = (
        db.scalars(
            query.order_by(
                PreRegistration.created_at.desc()
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(page_size)
        )
        .all()
    )

    items = [
        PreRegistrationResponse.model_validate(
            record
        )
        for record in records
    ]

    verified_count = (
        db.scalar(
            select(func.count())
            .select_from(PreRegistration)
            .where(
                PreRegistration.verified.is_(True)
            )
        )
        or 0
    )

    subscribed_count = (
        db.scalar(
            select(func.count())
            .select_from(PreRegistration)
            .where(
                PreRegistration.verified.is_(True),
                PreRegistration.subscribed.is_(True),
            )
        )
        or 0
    )

    sent_count = (
        db.scalar(
            select(func.count())
            .select_from(PreRegistration)
            .where(
                PreRegistration.launch_email_sent_at.is_not(
                    None
                )
            )
        )
        or 0
    )

    return AdminPreRegistrationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        verified_count=verified_count,
        subscribed_count=subscribed_count,
        sent_count=sent_count,
    )


def _send_launch_campaign(
    subject: str,
    message: str,
) -> None:
    """Send the launch campaign using an independent database session."""
    db = SessionLocal()

    try:
        service = PreRegistrationService(
            db=db,
            email_service=EmailService(settings),
            frontend_url=settings.FRONTEND_URL,
        )

        service.send_launch_campaign(
            subject=subject,
            message=message,
        )

    finally:
        db.close()


@router.post(
    "/send",
    response_model=LaunchEmailResponse,
)
def send_launch_email(
    payload: LaunchEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> LaunchEmailResponse:
    """Queue the launch email campaign."""
    eligible = (
        db.scalar(
            select(func.count())
            .select_from(PreRegistration)
            .where(
                PreRegistration.verified.is_(True),
                PreRegistration.subscribed.is_(True),
                PreRegistration.launch_email_sent_at.is_(
                    None
                ),
            )
        )
        or 0
    )

    if eligible == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "There are no eligible "
                "pre-registered users."
            ),
        )

    background_tasks.add_task(
        _send_launch_campaign,
        payload.subject,
        payload.message,
    )

    return LaunchEmailResponse(
        queued=eligible,
        message=(
            f"Launch email queued for {eligible} "
            "eligible pre-registrations."
        ),
    )
