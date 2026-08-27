"""Service for handling email operations."""

import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

from app.core.config import settings

logger = logging.getLogger(__name__)

# Force socket to use IPv4
orig_getaddrinfo = socket.getaddrinfo


def getaddrinfo_ipv4(*args: Any, **kwargs: Any) -> Any:
    # AF_INET is the address family for IPv4
    args_list = list(args)
    if len(args_list) >= 3:
        args_list[2] = socket.AF_INET
    else:
        kwargs['family'] = socket.AF_INET
    return orig_getaddrinfo(*args, **kwargs)


socket.getaddrinfo = getaddrinfo_ipv4


class EmailService:
    """Service providing methods to send various types of emails."""

    @staticmethod
    def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
        """Send email via SMTP with optional plain-text fallback.

        Args:
            to (str): To string.
            subject (str): Subject string.
            html (str): Html string.
            text (str): Text string.
        Returns:
            bool: True if successful, False otherwise.
        """
        if settings.DEMO_MODE:
            # Fixed: Use lazy % formatting to satisfy Pylint W1203
            print("DEMO Hello")
            logger.info("[DEMO EMAIL] %s | %s", to, subject)
            return True

        if settings.ENVIRONMENT == "production":
            return EmailService._send_via_brevo_api(to, subject, html, text)

        return EmailService._send_via_smtp(to, subject, html, text)

    @staticmethod
    def _send_via_brevo_api(to: str, subject: str, html: str, text: str | None = None) -> bool:
        if requests is None:
            logger.error(
                "The 'requests' library is required to send email via Brevo API.")
            return False
        api_key = getattr(settings, "BREVO_API_KEY", None)
        if not api_key:
            logger.error(
                "BREVO_API_KEY is missing in production environment variables.")
            return False

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json"
        }
        payload = {
            "sender": {
                "name": settings.EMAIL_FROM_NAME,
                "email": settings.EMAIL_FROM
            },
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html
        }

        if text:
            payload["textContent"] = text

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201, 202):
                return True
            else:
                logger.error("Brevo API error: %s", response.text)
                return False
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to send email via Brevo API to %s", to)
            return False

    @staticmethod
    def _send_via_smtp(to: str, subject: str, html: str, text: str | None = None) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr(
                (settings.EMAIL_FROM_NAME, settings.EMAIL_FROM))
            msg["To"] = to
            msg["Subject"] = subject

            plain_text = text or "Please view this email in an HTML-compatible email-client."
            msg.attach(MIMEText(plain_text, "plain_text", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            smtp_cls = smtplib.SMTP_SSL if settings.SMTP_SSL_TLS else smtplib.SMTP

            with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if not settings.SMTP_SSL_TLS and settings.SMTP_STARTTLS:
                    server.starttls()

                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                server.sendmail(settings.EMAIL_FROM, [to], msg.as_string())

            return True

        except (smtplib.SMTPException, OSError):
            # Fixed: Removed unused 'e', and caught specific exceptions (W0718)
            logger.exception("Failed to send email to %s", to)
            return False

    @staticmethod
    def send_reset_code(email: str, code: str, username: str = "User") -> bool:
        """Send password reset verfication code via email.

        Args:
            email (str): Email address.
            code (str): Verification or reset code.
            username (str): Username.

        Returns:
            bool: True if successful, False otherwise.
        """

        subject = f"{code} is your password reset code"
        text = (
            f"Hello {username},\n\n"
            f"Your password reset code is: {code}\n\n"
            "This code will expire in 15 minutes. "
            "If you did not request a password reset, please ignore this email."
        )

        html = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <style>
                body {{
                  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                  line-height: 1.6;
                  color: #1f2937;
                  margin: 0;
                  padding: 24px;
                  background-color: #f9fafb;
                }}
                .container {{
                  max-width: 480px;
                  margin: 0 auto;
                  background: #ffffff;
                  border: 1px solid #e5e7eb;
                  border-radius: 8px;
                  padding: 32px;
                }}
                .code-box {{
                  background-color: #f3f4f6;
                  border: 1px solid #e5e7eb;
                  border-radius: 6px;
                  padding: 16px;
                  text-align: center;
                  font-size: 32px;
                  font-weight: 700;
                  letter-spacing: 6px;
                  color: #111827;
                  margin: 24px 0;
                }}
                .footer {{
                  margin-top: 24px;
                  font-size: 12px;
                  color: #6b7280;
                  text-align: center;
                }}
              </style>
            </head>
            <body>
              <div class="container">
                <h2 style="margin-top: 0;">Password Reset Request</h2>
                <p>Hello <strong>{username}</strong>,</p>
                <p>Use the code below to complete your password reset request:</p>
                <div class="code-box">{code}</div>
                <p>This code will expire in <strong>15 minutes</strong>. If you did not request a password reset, ignore this email.</p>
                <div class="footer">
                  <p>&copy; {settings.APP_NAME}. All rights reserved.</p>
                </div>
              </div>
            </body>
            </html>
        """
        return EmailService.send_email(email, subject, html, text=text)
