"""SMTP email alerts."""
import logging
import smtplib
from email.message import EmailMessage

import config

logger = logging.getLogger(__name__)


class MailError(Exception):
    """Raised when an alert email could not be sent."""


def send_email(to_address, subject, body):
    if not (config.SMTP_HOST and config.SMTP_FROM):
        raise MailError("SMTP is not configured (set SMTP_HOST and SMTP_FROM/SMTP_USERNAME)")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.SMTP_FROM
    message["To"] = to_address
    message.set_content(body)

    try:
        if config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30)
        with server:
            if config.SMTP_USE_TLS and config.SMTP_PORT != 465:
                server.starttls()
            if config.SMTP_USERNAME:
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"sending email failed: {exc}") from exc

    logger.info("Sent alert email to %s", to_address)
