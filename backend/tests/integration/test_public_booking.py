from typing import Any

import httpx

from tests.conftest import BOOK_DAY, auth, book


async def test_public_business_and_services(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    r = await client.get("/public/glow-salon")
    assert r.status_code == 200
    assert r.json() == {
        "name": "Glow Salon",
        "slug": "glow-salon",
        "phone": "+919876543210",
        "timezone": "Asia/Kolkata",
        "assistant_enabled": False,
    }

    await client.delete(f"/services/{glow['services']['Beard Trim']}", headers=auth(glow["token"]))
    names = [s["name"] for s in (await client.get("/public/glow-salon/services")).json()]
    assert names == ["Haircut", "Haircut + Beard"]  # inactive hidden


async def test_unknown_slug_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/public/no-such-biz")
    assert r.status_code == 404
    assert r.json() == {"error": "BUSINESS_NOT_FOUND", "message": "Business not found"}


async def test_slots_respect_hours_and_bookings(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    sid = glow["services"]["Haircut"]
    r = await client.get("/public/glow-salon/slots", params={"service_id": sid, "date": BOOK_DAY})
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert slots[0] == "2026-10-10T10:00:00+05:30"
    assert "2026-10-10T17:30:00+05:30" in slots

    assert (
        await book(client, "glow-salon", glow["services"]["Haircut + Beard"], "2026-10-10T17:30:00+05:30")
    ).status_code == 201
    slots = (
        await client.get("/public/glow-salon/slots", params={"service_id": sid, "date": BOOK_DAY})
    ).json()["slots"]
    for blocked in ("17:15", "17:30", "17:45", "18:00"):
        assert f"2026-10-10T{blocked}:00+05:30" not in slots
    assert "2026-10-10T18:15:00+05:30" in slots


async def test_monday_closed_has_no_slots(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    r = await client.get(
        "/public/glow-salon/slots", params={"service_id": glow["services"]["Haircut"], "date": "2026-10-12"}
    )
    assert r.status_code == 200 and r.json()["slots"] == []


async def test_slots_past_date_422(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    r = await client.get(
        "/public/glow-salon/slots", params={"service_id": glow["services"]["Haircut"], "date": "2026-10-01"}
    )
    assert r.status_code == 422 and r.json()["error"] == "PAST_DATE"


async def test_booking_happy_path_matches_brief_sample(
    client: httpx.AsyncClient, glow: dict[str, Any]
) -> None:
    r = await book(client, "glow-salon", glow["services"]["Haircut + Beard"], "2026-10-10T17:30:00+05:30")
    assert r.status_code == 201
    assert r.json() == {
        "booking_id": "APT-20261010-0001",
        "service": "Haircut + Beard",
        "start_time": "2026-10-10T17:30:00+05:30",
        "end_time": "2026-10-10T18:15:00+05:30",
        "status": "booked",
        "message": "Booking confirmed at Glow Salon, Sat 10 Oct, 5:30 PM",
    }


async def test_booking_refs_increment_per_day(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    sid = glow["services"]["Haircut"]
    r1 = await book(client, "glow-salon", sid, "2026-10-10T10:00:00+05:30")
    r2 = await book(client, "glow-salon", sid, "2026-10-10T11:00:00+05:30", phone="9000000001")
    r3 = await book(client, "glow-salon", sid, "2026-10-11T11:00:00+05:30")
    assert [r.json()["booking_id"] for r in (r1, r2, r3)] == [
        "APT-20261010-0001",
        "APT-20261010-0002",
        "APT-20261011-0001",
    ]


async def test_utc_start_time_accepted(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    r = await book(client, "glow-salon", glow["services"]["Haircut"], "2026-10-10T12:00:00Z")  # 17:30 IST
    assert r.status_code == 201
    assert r.json()["start_time"] == "2026-10-10T17:30:00+05:30"


async def test_off_grid_and_outside_hours_422(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    sid = glow["services"]["Haircut"]
    off = await book(client, "glow-salon", sid, "2026-10-10T17:10:00+05:30")
    assert off.status_code == 422 and off.json()["error"] == "OFF_GRID"
    out = await book(client, "glow-salon", sid, "2026-10-10T13:00:00+05:30")
    assert out.status_code == 422 and out.json()["error"] == "OUTSIDE_HOURS"
    closed = await book(client, "glow-salon", sid, "2026-10-12T11:00:00+05:30")
    assert closed.status_code == 422 and closed.json()["error"] == "OUTSIDE_HOURS"


async def test_invalid_phone_and_name_422(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    sid = glow["services"]["Haircut"]
    r = await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30", phone="12345")
    assert r.status_code == 422 and "phone" in r.json()["message"]
    r = await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30", name="A")
    assert r.status_code == 422


async def test_service_of_other_business_or_inactive_404(
    client: httpx.AsyncClient, glow: dict[str, Any]
) -> None:
    from tests.conftest import create_business

    other = await create_business(client, "care-physio", name="Care Physio")
    r = await book(client, "glow-salon", other["services"]["Haircut"], "2026-10-10T17:30:00+05:30")
    assert r.status_code == 404 and r.json()["error"] == "SERVICE_NOT_FOUND"

    await client.delete(f"/services/{glow['services']['Haircut']}", headers=auth(glow["token"]))
    r = await book(client, "glow-salon", glow["services"]["Haircut"], "2026-10-10T17:30:00+05:30")
    assert r.status_code == 404


async def test_same_slot_twice_409_and_cancelled_slot_rebookable(
    client: httpx.AsyncClient, glow: dict[str, Any]
) -> None:
    sid = glow["services"]["Haircut"]
    first = await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30")
    assert first.status_code == 201
    second = await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30", phone="9000000002")
    assert second.status_code == 409
    assert second.json() == {
        "error": "SLOT_TAKEN",
        "message": "This slot was just booked. Please pick another time.",
    }

    appts = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=auth(glow["token"]))).json()
    await client.patch(
        f"/appointments/{appts[0]['id']}", json={"status": "cancelled"}, headers=auth(glow["token"])
    )
    again = await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30", phone="9000000002")
    assert again.status_code == 201


async def test_repeat_customer_reuses_row(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    sid = glow["services"]["Haircut"]
    await book(client, "glow-salon", sid, "2026-10-10T10:00:00+05:30", name="Ravi")
    await book(client, "glow-salon", sid, "2026-10-10T11:00:00+05:30", name="Ravi K", phone="+91 91234 56780")
    appts = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=auth(glow["token"]))).json()
    assert {a["customer_phone"] for a in appts} == {"+919123456780"}
    assert {a["customer_name"] for a in appts} == {"Ravi K"}  # latest name wins
