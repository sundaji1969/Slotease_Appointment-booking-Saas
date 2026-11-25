from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import jwt
import pytest

from app.config import settings
from app.core.formatting import confirmation_text, human_datetime, whatsapp_url
from app.core.phone import normalize_indian_phone
from app.core.security import (
    InvalidToken,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.stats import no_show_rate

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize(
    "raw", ["9876543210", "+91 98765 43210", "919876543210", "09876543210", "98765-43210"]
)
def test_phone_normalised_to_e164(raw: str) -> None:
    assert normalize_indian_phone(raw) == "+919876543210"


@pytest.mark.parametrize("raw", ["", "12345", "5876543210", "98765432101", "abcdefghij"])
def test_invalid_phone_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_indian_phone(raw)


def test_human_datetime_matches_brief_format() -> None:
    assert human_datetime(datetime(2026, 10, 10, 17, 30, tzinfo=IST)) == "Sat 10 Oct, 5:30 PM"
    assert human_datetime(datetime(2026, 10, 1, 0, 5, tzinfo=IST)) == "Thu 1 Oct, 12:05 AM"
    assert human_datetime(datetime(2026, 10, 1, 12, 0, tzinfo=IST)) == "Thu 1 Oct, 12:00 PM"


def test_confirmation_text_and_whatsapp_url() -> None:
    text = confirmation_text("Glow Salon", datetime(2026, 10, 10, 17, 30, tzinfo=IST), "APT-20261010-0007")
    assert text == "Booking confirmed at Glow Salon, Sat 10 Oct, 5:30 PM. Ref APT-20261010-0007."
    url = whatsapp_url("+919123456780", text)
    assert url.startswith("https://wa.me/919123456780?text=Booking%20confirmed%20at%20Glow%20Salon")


def test_no_show_rate() -> None:
    assert no_show_rate(0, 0) == 0.0
    assert no_show_rate(8, 2) == 0.2


def test_password_hashing() -> None:
    h = hash_password("Passw0rd!")
    assert h != "Passw0rd!" and h.startswith("$2")
    assert verify_password("Passw0rd!", h)
    assert not verify_password("wrong", h)


def test_token_roundtrip_and_tamper() -> None:
    import uuid

    uid, bid = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(uid, bid, "owner")
    claims = decode_access_token(token)
    assert (claims.user_id, claims.business_id, claims.role) == (uid, bid, "owner")
    with pytest.raises(InvalidToken):
        decode_access_token(token[:-2] + ("A" if token[-1] != "A" else "B") + token[-1])


def test_expired_token_rejected() -> None:
    import uuid

    past = datetime.now(IST) - timedelta(hours=2)
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "bid": str(uuid.uuid4()), "role": "owner", "exp": int(past.timestamp())},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(InvalidToken):
        decode_access_token(token)
