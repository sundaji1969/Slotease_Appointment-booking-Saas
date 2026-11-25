from typing import Any

import httpx
import pytest

from app.services import notify
from app.services.booking import BookingNotice
from tests.conftest import book


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[BookingNotice]:
    calls: list[BookingNotice] = []
    monkeypatch.setattr(notify, "notify_new_booking", calls.append)
    return calls


async def test_notify_once_per_success_never_on_409(
    client: httpx.AsyncClient, glow: dict[str, Any], sent: list[BookingNotice]
) -> None:
    sid = glow["services"]["Haircut"]
    assert (await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30")).status_code == 201
    assert (
        await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30", phone="9000000001")
    ).status_code == 409
    assert (await book(client, "glow-salon", sid, "2026-10-10T17:10:00+05:30")).status_code == 422
    assert len(sent) == 1
    assert sent[0].public_ref == "APT-20261010-0001"
    assert sent[0].customer_phone == "+919123456780"


async def test_email_failure_never_breaks_booking(
    client: httpx.AsyncClient, glow: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("resend down")

    monkeypatch.setattr(notify, "send_email", boom)
    r = await book(client, "glow-salon", glow["services"]["Haircut"], "2026-10-10T17:30:00+05:30")
    assert r.status_code == 201


async def test_owner_email_sent_with_whatsapp_link(
    client: httpx.AsyncClient, glow: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    emails: list[tuple[list[str], str, str]] = []
    monkeypatch.setattr(notify, "send_email", lambda to, subject, body: emails.append((to, subject, body)))
    await book(client, "glow-salon", glow["services"]["Haircut"], "2026-10-10T17:30:00+05:30")
    assert len(emails) == 1
    to, subject, body = emails[0]
    assert to == ["owner@glow-salon.test"]
    assert "Sat 10 Oct, 5:30 PM" in subject
    assert "https://wa.me/919123456780?text=" in body
