from __future__ import annotations

import html
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when email delivery fails."""


class EmailService:
    """Centralized service for transactional email delivery."""

    def __init__(
        self,
        app_settings: Settings | None = None,
    ) -> None:
        self.settings = app_settings or settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        text: str,
        html_body: str | None = None,
    ) -> None:
        """Send an email using the configured provider.

        Development/staging:
            SMTP

        Production:
            Brevo API

        Demo mode:
            Logs the email without sending it.
        """
        if self.settings.DEMO_MODE:
            logger.info(
                "[DEMO EMAIL] recipient=%s subject=%s",
                recipient,
                subject,
            )
            return

        html_content = (
            html_body
            if html_body
            else f"<pre>{html.escape(text)}</pre>"
        )

        if self.settings.ENVIRONMENT == "production":
            self._send_via_brevo(
                recipient=recipient,
                subject=subject,
                html_body=html_content,
                text=text,
            )
            return

        self._send_via_smtp(
            recipient=recipient,
            subject=subject,
            html_body=html_content,
            text=text,
        )

    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> bool:
        """Backward-compatible boolean email API."""
        try:
            self.send(
                recipient=to,
                subject=subject,
                text=(
                    text
                    or "Please view this email in an HTML-compatible "
                    "email client."
                ),
                html_body=html,
            )
            return True

        except EmailDeliveryError:
            return False

    # ------------------------------------------------------------------
    # Pre-registration verification
    # ------------------------------------------------------------------

    def send_verification_email(
        self,
        *,
        recipient: str,
        name: str | None,
        verification_url: str,
    ) -> None:
        """Send the double-opt-in verification email."""
        display_name = (name or "there").strip()

        safe_name = html.escape(display_name)
        safe_url = html.escape(
            verification_url,
            quote=True,
        )

        text = f"""Hi {display_name},

Thanks for registering your interest in My Stuff.

Please confirm your email address using this link:

{verification_url}

This link expires in 48 hours.

You will only receive the My Stuff launch announcement and important
pre-launch updates.

— The My Stuff team
"""

        html_body = f"""\
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>Confirm your My Stuff registration</title>
</head>
<body
    style="
        margin: 0;
        padding: 32px 16px;
        background: #f6f6f3;
        color: #1c2321;
        font-family: Arial, Helvetica, sans-serif;
    "
>
    <div
        style="
            max-width: 560px;
            margin: 0 auto;
            padding: 32px;
            background: #ffffff;
            border: 1px solid #e5e5df;
            border-radius: 12px;
        "
    >
        <h1>Welcome to My Stuff</h1>

        <p>Hi {safe_name},</p>

        <p>
            Thanks for registering your interest in My Stuff.
        </p>

        <p>
            Please confirm your email address to join the launch list.
        </p>

        <p style="margin: 28px 0;">
            <a
                href="{safe_url}"
                style="
                    display: inline-block;
                    padding: 12px 20px;
                    background: #2f5d50;
                    color: #ffffff;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                "
            >
                Confirm my email
            </a>
        </p>

        <p style="font-size: 14px; color: #666;">
            This link expires in 48 hours.
        </p>

        <p style="font-size: 13px; color: #777;">
            If you did not register for My Stuff,
            you can safely ignore this email.
        </p>

        <hr>

        <p style="font-size: 12px; color: #777;">
            — The My Stuff team
        </p>
    </div>
</body>
</html>
"""

        self.send(
            recipient=recipient,
            subject="Confirm your My Stuff pre-registration",
            text=text,
            html_body=html_body,
        )

    # ------------------------------------------------------------------
    # Launch campaign
    # ------------------------------------------------------------------

    def send_launch_email(
        self,
        *,
        recipient: str,
        name: str | None,
        subject: str,
        message: str,
        unsubscribe_url: str,
    ) -> None:
        """Send the My Stuff launch announcement."""
        display_name = (name or "there").strip()

        safe_name = html.escape(display_name)

        safe_frontend_url = html.escape(
            self.settings.FRONTEND_URL,
            quote=True,
        )

        safe_unsubscribe_url = html.escape(
            unsubscribe_url,
            quote=True,
        )

        text = f"""Hi {display_name},

{message}

My Stuff is ready.

Open My Stuff:
{self.settings.FRONTEND_URL}

Don't want launch emails anymore?
{unsubscribe_url}

— The My Stuff team
"""

        paragraphs = "\n".join(
            f"<p>{html.escape(part.strip())}</p>"
            for part in message.split("\n\n")
            if part.strip()
        )

        html_body = f"""\
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>{html.escape(subject)}</title>
</head>
<body
    style="
        margin: 0;
        padding: 32px 16px;
        background: #f6f6f3;
        color: #1c2321;
        font-family: Arial, Helvetica, sans-serif;
    "
>
    <div
        style="
            max-width: 560px;
            margin: 0 auto;
            padding: 32px;
            background: #ffffff;
            border: 1px solid #e5e5df;
            border-radius: 12px;
        "
    >
        <h1>My Stuff is here</h1>

        <p>Hi {safe_name},</p>

        {paragraphs}

        <p style="margin: 28px 0;">
            <a
                href="{safe_frontend_url}"
                style="
                    display: inline-block;
                    padding: 12px 20px;
                    background: #2f5d50;
                    color: #ffffff;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                "
            >
                Open My Stuff
            </a>
        </p>

        <hr>

        <p
            style="
                margin: 0;
                font-size: 12px;
                color: #777;
                text-align: center;
            "
        >
            <a
                href="{safe_unsubscribe_url}"
                style="color: #777;"
            >
                Unsubscribe from launch emails
            </a>
        </p>
    </div>
</body>
</html>
"""

        self.send(
            recipient=recipient,
            subject=subject,
            text=text,
            html_body=html_body,
        )

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    def send_reset_code(
        self,
        email: str,
        code: str,
        username: str = "User",
    ) -> bool:
        """Send a password reset code."""
        safe_username = html.escape(username)
        safe_code = html.escape(code)

        subject = f"{code} is your password reset code"

        text = (
            f"Hello {username},\n\n"
            f"Your password reset code is: {code}\n\n"
            "This code will expire in 15 minutes. "
            "If you did not request a password reset, "
            "please ignore this email."
        )

        html_body = f"""\
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>Password Reset</title>
</head>
<body
    style="
        margin: 0;
        padding: 24px 16px;
        background: #f9fafb;
        color: #1f2937;
        font-family: Arial, Helvetica, sans-serif;
    "
>
    <div
        style="
            max-width: 480px;
            margin: 0 auto;
            padding: 32px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
        "
    >
        <h2>Password Reset Request</h2>

        <p>
            Hello <strong>{safe_username}</strong>,
        </p>

        <p>
            Use the code below to complete your password reset request:
        </p>

        <div
            style="
                margin: 24px 0;
                padding: 16px;
                background: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                text-align: center;
                font-size: 32px;
                font-weight: 700;
                letter-spacing: 6px;
            "
        >
            {safe_code}
        </div>

        <p>
            This code will expire in <strong>15 minutes</strong>.
        </p>

        <p>
            If you did not request a password reset,
            you can safely ignore this email.
        </p>

        <p
            style="
                margin-top: 24px;
                font-size: 12px;
                color: #6b7280;
                text-align: center;
            "
        >
            &copy; {html.escape(self.settings.APP_NAME)}
        </p>
    </div>
</body>
</html>
"""

        try:
            self.send(
                recipient=email,
                subject=subject,
                text=text,
                html_body=html_body,
            )
            return True

        except EmailDeliveryError:
            return False

    # ------------------------------------------------------------------
    # Brevo
    # ------------------------------------------------------------------

    def _send_via_brevo(
        self,
        *,
        recipient: str,
        subject: str,
        html_body: str,
        text: str,
    ) -> None:
        """Send an email using Brevo."""
        if requests is None:
            raise EmailDeliveryError(
                "The requests package is required for Brevo."
            )

        api_key = self.settings.BREVO_API_KEY

        if not api_key:
            raise EmailDeliveryError(
                "BREVO_API_KEY is not configured."
            )

        payload: dict[str, Any] = {
            "sender": {
                "name": self.settings.EMAIL_FROM_NAME,
                "email": self.settings.EMAIL_FROM,
            },
            "to": [
                {
                    "email": recipient,
                },
            ],
            "subject": subject,
            "htmlContent": html_body,
            "textContent": text,
        }

        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        }

        try:
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload,
                headers=headers,
                timeout=10,
            )

        except requests.RequestException as exc:
            logger.exception(
                "Brevo request failed for %s",
                recipient,
            )

            raise EmailDeliveryError(
                f"Brevo request failed: {exc}",
            ) from exc

        if response.status_code not in (200, 201, 202):
            logger.error(
                "Brevo API error: status=%s body=%s",
                response.status_code,
                response.text,
            )

            raise EmailDeliveryError(
                f"Brevo returned HTTP {response.status_code}.",
            )

    # ------------------------------------------------------------------
    # SMTP
    # ------------------------------------------------------------------

    def _send_via_smtp(
        self,
        *,
        recipient: str,
        subject: str,
        html_body: str,
        text: str,
    ) -> None:
        """Send an email using SMTP."""
        message = EmailMessage()

        message["From"] = formataddr(
            (
                self.settings.EMAIL_FROM_NAME,
                self.settings.EMAIL_FROM,
            ),
        )

        message["To"] = recipient
        message["Subject"] = subject

        message.set_content(text)

        message.add_alternative(
            html_body,
            subtype="html",
        )

        try:
            if self.settings.SMTP_SSL_TLS:
                smtp = smtplib.SMTP_SSL(
                    self.settings.SMTP_HOST,
                    self.settings.SMTP_PORT,
                    timeout=30,
                )
            else:
                smtp = smtplib.SMTP(
                    self.settings.SMTP_HOST,
                    self.settings.SMTP_PORT,
                    timeout=30,
                )

            with smtp as server:
                server.ehlo()

                if (
                    not self.settings.SMTP_SSL_TLS
                    and self.settings.SMTP_STARTTLS
                ):
                    server.starttls()
                    server.ehlo()

                if (
                    self.settings.SMTP_USER
                    and self.settings.SMTP_PASSWORD
                ):
                    server.login(
                        self.settings.SMTP_USER,
                        self.settings.SMTP_PASSWORD,
                    )

                server.send_message(message)

        except (
            smtplib.SMTPException,
            OSError,
        ) as exc:
            logger.exception(
                "SMTP delivery failed for %s",
                recipient,
            )

            raise EmailDeliveryError(
                f"SMTP delivery failed: {exc}",
            ) from exc
