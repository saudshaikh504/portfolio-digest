"""
sender.py — Sends the digest email via Gmail SMTP.
Uses a Gmail App Password for authentication.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SENDER_EMAIL, RECIPIENT_EMAIL, GMAIL_APP_PASSWORD

logger    = logging.getLogger(__name__)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(subject: str, html_body: str) -> bool:
    """
    Send an HTML email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    if not GMAIL_APP_PASSWORD:
        logger.error("GMAIL_APP_PASSWORD is not set — cannot send email.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Portfolio Digest <{SENDER_EMAIL}>"
    msg["To"]      = RECIPIENT_EMAIL

    plain = (
        "Your Portfolio Intelligence Digest is ready.\n"
        "View this email in an HTML-capable client for the full report."
    )
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {RECIPIENT_EMAIL}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            f"Gmail SMTP authentication failed: {e}. "
            "Make sure you are using a Gmail App Password."
        )
        return False
    except Exception as e:
        logger.error(f"Unexpected email send error: {e}")
        return False
