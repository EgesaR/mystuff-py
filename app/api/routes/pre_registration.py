from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.schemas.pre_registration import (
    PreRegistrationCreate,
    PreRegistrationSignupResponse,
    PreRegistrationUnsubscribeResponse,
    PreRegistrationVerifyResponse,
)
from app.services.email_service import EmailService
from app.services.pre_registration_service import (
    PreRegistrationService,
)

router = APIRouter()


def get_email_service() -> EmailService:
    """Return the configured email service."""
    return EmailService(settings)


def get_pre_registration_service(
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> PreRegistrationService:
    """Return the configured pre-registration service."""
    return PreRegistrationService(
        db=db,
        email_service=email_service,
        frontend_url=settings.FRONTEND_URL,
    )


@router.post(
    "",
    response_model=PreRegistrationSignupResponse,
)
def pre_register(
    payload: PreRegistrationCreate,
    service: PreRegistrationService = Depends(
        get_pre_registration_service,
    ),
) -> PreRegistrationSignupResponse:
    """Register an email for the upcoming My Stuff launch."""
    normalized_email = str(
        payload.email,
    ).strip().lower()

    service.create_or_refresh(
        email=normalized_email,
        name=payload.name,
    )

    return PreRegistrationSignupResponse(
        message=(
            "You're on the list. "
            "Check your email to confirm your address."
        ),
    )


@router.get(
    "/verify",
    response_model=PreRegistrationVerifyResponse,
)
def verify_pre_registration(
    token: str = Query(
        ...,
        min_length=20,
    ),
    service: PreRegistrationService = Depends(
        get_pre_registration_service,
    ),
) -> PreRegistrationVerifyResponse:
    """Verify a pre-registration email address."""
    verified = service.verify(token)

    if not verified:
        raise HTTPException(
            status_code=400,
            detail=(
                "This verification link is invalid or expired."
            ),
        )

    return PreRegistrationVerifyResponse(
        verified=True,
        message="Your email has been confirmed.",
    )


@router.get(
    "/unsubscribe",
    response_model=PreRegistrationUnsubscribeResponse,
)
def unsubscribe(
    token: str = Query(
        ...,
        min_length=20,
    ),
    service: PreRegistrationService = Depends(
        get_pre_registration_service,
    ),
) -> PreRegistrationUnsubscribeResponse:
    """Unsubscribe an address from My Stuff launch emails."""
    unsubscribed = service.unsubscribe(token)

    if not unsubscribed:
        raise HTTPException(
            status_code=404,
            detail="Subscription could not be found.",
        )

    return PreRegistrationUnsubscribeResponse(
        subscribed=False,
        message="You have been unsubscribed.",
    )
