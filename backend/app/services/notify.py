"""Notifications. Runs in FastAPI BackgroundTasks; a failure here must never affect a booking."""

import logging

import httpx

from app.config import settings
from app.core.formatting import confirmation_text, human_datetime, whatsapp_url
from app.db import SessionLocal
from app.repositories import users as user_repo
from app.services.booking import BookingNotice

log = logging.getLogger("slotease.notify")

RESEND_URL = "https://api.resend.com/emails"


def send_email(to: list[str], subject: str, body: str) -> None:
    if not settings.RESEND_API_KEY:
        log.info("email (dev mode, not sent) to=%s subject=%s\n%s", to, subject, body)
        return
    resp = httpx.post(
        RESEND_URL,
        headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
        json={"from": settings.RESEND_FROM, "to": to, "subject": subject, "text": body},
        timeout=10,
    )
    resp.raise_for_status()


def owner_email_body(n: BookingNotice) -> str:
    confirm = confirmation_text(n.business_name, n.start_local, n.public_ref)
    return (
        f"New booking {n.public_ref}\n\n"
        f"Customer: {n.customer_name} ({n.customer_phone})\n"
        f"Service:  {n.service_name}\n"
        f"When:     {human_datetime(n.start_local)}\n\n"
        f"Confirm on WhatsApp with one tap:\n{whatsapp_url(n.customer_phone, confirm)}\n\n"
        f"Dashboard: {settings.APP_BASE_URL}/dashboard\n"
    )


def notify_new_booking(notice: BookingNotice) -> None:
    try:
        with SessionLocal() as db:
            recipients = user_repo.owner_emails(db, notice.business_id)
        if recipients:
            send_email(
                recipients,
                f"New booking: {notice.customer_name}, {human_datetime(notice.start_local)}",
                owner_email_body(notice),
            )
    except Exception:  # never propagate
        log.exception("failed to send booking notification for %s", notice.public_ref)
