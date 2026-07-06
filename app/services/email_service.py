"""Service for handling email operations."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service providing methods to send various types of emails."""

    @staticmethod
    def send_email(to: str, subject: str, html: str) -> bool:
        """Sends an email via SMTP or logs it if in demo mode."""
        if settings.DEMO_MODE:
            # Fixed: Use lazy % formatting to satisfy Pylint W1203
            logger.info("[DEMO EMAIL] %s | %s", to, subject)
            return True

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as s:
                s.starttls()

                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

                s.sendmail(settings.EMAIL_FROM, [to], msg.as_string())

            return True

        except (smtplib.SMTPException, OSError):
            # Fixed: Removed unused 'e', and caught specific exceptions (W0718)
            logger.exception("Email sending failed")
            return False

    @staticmethod
    def send_reset_code(email: str, code: str, username: str) -> bool:
        """Sends a password reset code email."""
        html = f"""
        <h2>Password Reset</h2>
        <p>Hello {username},</p>
        <p>Your reset code is:</p>
        <h3>{code}</h3>
        """
        return EmailService.send_email(email, "Password Reset Code", html)
