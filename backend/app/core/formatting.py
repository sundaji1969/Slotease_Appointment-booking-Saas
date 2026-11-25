from datetime import datetime
from urllib.parse import quote


def human_datetime(dt: datetime) -> str:
    """'Sat 10 Oct, 5:30 PM' — platform independent (no %-d / %-I)."""
    hour12 = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt:%a} {dt.day} {dt:%b}, {hour12}:{dt.minute:02d} {ampm}"


def confirmation_text(business_name: str, start_local: datetime, public_ref: str) -> str:
    return f"Booking confirmed at {business_name}, {human_datetime(start_local)}. Ref {public_ref}."


def whatsapp_url(phone_e164: str, text: str) -> str:
    digits = "".join(ch for ch in phone_e164 if ch.isdigit())
    return f"https://wa.me/{digits}?text={quote(text)}"
