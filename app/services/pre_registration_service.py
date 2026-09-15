from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pre_registration import PreRegistration
from app.services.email_service import (
    EmailDeliveryError,
    EmailService,
)

VERIFICATION_EXPIRY_HOURS = 48


class PreRegistrationService:
    """Business logic for the My Stuff pre-registration system."""

    def __init__(
        self,
        db: Session,
        email_service: EmailService,
        frontend_url: str,
    ) -> None:
        self.db = db
        self.email_service = email_service
        self.frontend_url = frontend_url.rstrip("/")

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_token(token: str) -> str:
        """Return the SHA-256 hash of a token."""
        return hashlib.sha256(
            token.encode("utf-8"),
        ).hexdigest()

    @classmethod
    def _generate_token(cls) -> tuple[str, str]:
        """Generate a raw token and its hash."""
        token = secrets.token_urlsafe(48)

        return token, cls._hash_token(token)

    @staticmethod
    def _make_unsubscribe_token(
        user: PreRegistration,
    ) -> str:
        """Create a deterministic unsubscribe token.

        The raw token is never stored.

        It is derived from:
            SECRET_KEY + registration ID

        Only its hash is stored in the database.
        """
        message = (
            f"unsubscribe:{user.id}"
        ).encode("utf-8")

        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()

    # ------------------------------------------------------------------
    # Create / refresh
    # ------------------------------------------------------------------

    def create_or_refresh(
        self,
        *,
        email: str,
        name: str | None,
    ) -> PreRegistration:
        """Create a pre-registration or refresh verification."""
        normalized_email = email.strip().lower()

        registration = self.db.scalar(
            select(PreRegistration).where(
                func.lower(PreRegistration.email)
                == normalized_email,
            ),
        )

        now = datetime.now(UTC)

        if registration is None:
            raw_token, token_hash = (
                self._generate_token()
            )

            registration = PreRegistration(
                email=normalized_email,
                name=name.strip() if name else None,
                verification_token_hash=token_hash,
                verification_expires_at=(
                    now
                    + timedelta(
                        hours=VERIFICATION_EXPIRY_HOURS,
                    )
                ),
                verified=False,
                subscribed=False,
            )

            self.db.add(registration)

            # Generate the UUID primary key and make it
            # available before creating the unsubscribe token.
            self.db.flush()

            unsubscribe_token = (
                self._make_unsubscribe_token(
                    registration,
                )
            )

            registration.unsubscribe_token_hash = (
                self._hash_token(
                    unsubscribe_token,
                )
            )

        else:
            if name:
                registration.name = name.strip()

            if registration.verified:
                return registration

            raw_token, token_hash = (
                self._generate_token()
            )

            registration.verification_token_hash = (
                token_hash
            )

            registration.verification_expires_at = (
                now
                + timedelta(
                    hours=VERIFICATION_EXPIRY_HOURS,
                )
            )

        self.db.commit()
        self.db.refresh(registration)

        verification_url = (
            f"{self.frontend_url}/pre-register/verify?"
            + urlencode(
                {
                    "token": raw_token,
                },
            )
        )

        self.email_service.send_verification_email(
            recipient=registration.email,
            name=registration.name,
            verification_url=verification_url,
        )

        return registration

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------

    def verify(self, token: str) -> bool:
        """Verify a pre-registration email."""
        token = token.strip()

        if not token:
            return False

        token_hash = self._hash_token(token)

        registration = self.db.scalar(
            select(PreRegistration).where(
                PreRegistration.verification_token_hash
                == token_hash,
            ),
        )

        if registration is None:
            return False

        now = datetime.now(UTC)

        expires_at = registration.verification_expires_at

        if (
            expires_at is not None
            and expires_at < now
        ):
            return False

        registration.verified = True
        registration.verified_at = now
        registration.subscribed = True

        registration.verification_token_hash = None
        registration.verification_expires_at = None

        self.db.commit()

        return True

    # ------------------------------------------------------------------
    # Unsubscribe
    # ------------------------------------------------------------------

    def unsubscribe(
        self,
        token: str,
    ) -> bool:
        """Unsubscribe a pre-registered user."""
        token = token.strip()

        if not token:
            return False

        token_hash = self._hash_token(token)

        registration = self.db.scalar(
            select(PreRegistration).where(
                PreRegistration.unsubscribe_token_hash
                == token_hash,
            ),
        )

        if registration is None:
            return False

        registration.subscribed = False
        registration.unsubscribed_at = (
            datetime.now(UTC)
        )

        self.db.commit()

        return True

    # ------------------------------------------------------------------
    # Launch campaign
    # ------------------------------------------------------------------

    def send_launch_campaign(
        self,
        *,
        subject: str,
        message: str,
    ) -> int:
        """Send the launch email to all eligible users."""
        users = self.db.scalars(
            select(PreRegistration).where(
                PreRegistration.verified.is_(True),
                PreRegistration.subscribed.is_(True),
                PreRegistration.launch_email_sent_at.is_(None),
            ),
        ).all()

        sent = 0

        for user in users:
            try:
                unsubscribe_token = (
                    self._make_unsubscribe_token(user)
                )

                unsubscribe_url = (
                    f"{self.frontend_url}"
                    "/pre-register/unsubscribe?"
                    + urlencode(
                        {
                            "token": unsubscribe_token,
                        },
                    )
                )

                self.email_service.send_launch_email(
                    recipient=user.email,
                    name=user.name,
                    subject=subject,
                    message=message,
                    unsubscribe_url=unsubscribe_url,
                )

                user.launch_email_sent_at = (
                    datetime.now(UTC)
                )

                user.last_email_error = None

                sent += 1

            except EmailDeliveryError as exc:
                user.last_email_error = str(exc)[:2000]

            self.db.commit()

        return sent
