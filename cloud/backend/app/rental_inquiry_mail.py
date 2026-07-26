"""Outbound email for public Mietanfrage submissions."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

from .env import is_production

log = logging.getLogger(__name__)


class RentalInquiryMailError(Exception):
    """Raised when inquiry mail cannot be delivered."""


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST", "").strip() and os.getenv("RENTAL_INQUIRY_TO", "").strip())


def send_rental_inquiry_email(
    *,
    name: str,
    organisation: str,
    email: str,
    phone: str | None,
    timeframe: str,
    message: str,
) -> None:
    """Send inquiry to ``RENTAL_INQUIRY_TO``.

    In non-production, when SMTP is unset, logs the message instead of sending.
    In production, missing SMTP configuration raises ``RentalInquiryMailError``.
    """
    to_addr = (os.getenv("RENTAL_INQUIRY_TO") or "").strip()
    subject = f"Mietanfrage: {organisation}"
    body = (
        f"Name: {name}\n"
        f"Organisation: {organisation}\n"
        f"E-Mail: {email}\n"
        f"Telefon: {phone or '—'}\n"
        f"Zeitraum: {timeframe}\n"
        f"\n"
        f"Nachricht:\n{message}\n"
    )

    if not _smtp_configured():
        if is_production():
            raise RentalInquiryMailError("SMTP or RENTAL_INQUIRY_TO is not configured")
        log.info(
            "rental_inquiry_dev_fallback to=%s subject=%s\n%s",
            to_addr or "(unset)",
            subject,
            body,
        )
        return

    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = (os.getenv("SMTP_USER") or "").strip()
    password = os.getenv("SMTP_PASSWORD") or ""
    from_addr = (os.getenv("SMTP_FROM") or user or to_addr).strip()
    use_tls = os.getenv("SMTP_TLS", "true").lower() != "false"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Reply-To"] = email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    except OSError as exc:
        log.exception("rental_inquiry_smtp_failed")
        raise RentalInquiryMailError("Failed to send rental inquiry email") from exc
