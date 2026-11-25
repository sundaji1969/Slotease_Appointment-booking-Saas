from typing import Any

import httpx
import pytest

from tests.conftest import BOOK_DAY, auth, book


async def test_appointments_by_date_and_range(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    sid = glow["services"]["Haircut"]
    await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30")
    await book(client, "glow-salon", sid, "2026-10-10T10:00:00+05:30", phone="9000000001")
    await book(client, "glow-salon", sid, "2026-10-13T10:00:00+05:30", phone="9000000002")
    h = auth(glow["token"])

    day = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=h)).json()
    assert [a["start_time"] for a in day] == ["2026-10-10T10:00:00+05:30", "2026-10-10T17:30:00+05:30"]
    a = day[1]
    assert a["service_name"] == "Haircut" and a["price"] == 300 and a["customer_name"] == "Ravi Kumar"
    assert a["whatsapp_url"].startswith("https://wa.me/919123456780?text=Booking%20confirmed")

    week = (
        await client.get("/appointments", params={"from": "2026-10-10", "to": "2026-10-16"}, headers=h)
    ).json()
    assert len(week) == 3
    limited = (
        await client.get(
            "/appointments", params={"from": "2026-10-10", "to": "2026-10-16", "limit": 1}, headers=h
        )
    ).json()
    assert len(limited) == 1
    too_many = await client.get("/appointments", params={"date": BOOK_DAY, "limit": 500}, headers=h)
    assert too_many.status_code == 422


@pytest.mark.parametrize("target", ["completed", "cancelled", "no_show"])
async def test_status_transitions(client: httpx.AsyncClient, glow: dict[str, Any], target: str) -> None:
    await book(client, "glow-salon", glow["services"]["Haircut"], "2026-10-10T17:30:00+05:30")
    h = auth(glow["token"])
    appt = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=h)).json()[0]
    r = await client.patch(f"/appointments/{appt['id']}", json={"status": target}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == target
    # terminal states cannot change
    r = await client.patch(f"/appointments/{appt['id']}", json={"status": "booked"}, headers=h)
    assert r.status_code == 422 and r.json()["error"] == "INVALID_TRANSITION"


async def test_invalid_status_value_422(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    await book(client, "glow-salon", glow["services"]["Haircut"], "2026-10-10T17:30:00+05:30")
    h = auth(glow["token"])
    appt = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=h)).json()[0]
    r = await client.patch(f"/appointments/{appt['id']}", json={"status": "teleported"}, headers=h)
    assert r.status_code == 422


async def test_services_crud_soft_delete(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    h = auth(glow["token"])
    created = await client.post(
        "/services", json={"name": "Facial", "duration_min": 60, "price": 999.5}, headers=h
    )
    assert created.status_code == 201
    sid = created.json()["id"]
    upd = await client.put(f"/services/{sid}", json={"price": 1099, "duration_min": 50}, headers=h)
    assert upd.json()["price"] == 1099 and upd.json()["duration_min"] == 50 and upd.json()["name"] == "Facial"
    deleted = await client.delete(f"/services/{sid}", headers=h)
    assert deleted.status_code == 200 and deleted.json()["is_active"] is False
    still_listed = [s["id"] for s in (await client.get("/services", headers=h)).json()]
    assert sid in still_listed  # owner still sees it (to reactivate)
    react = await client.put(f"/services/{sid}", json={"is_active": True}, headers=h)
    assert react.json()["is_active"] is True
    bad = await client.post("/services", json={"name": "X", "duration_min": 3, "price": 10}, headers=h)
    assert bad.status_code == 422


async def test_duration_change_does_not_alter_existing_appointments(
    client: httpx.AsyncClient, glow: dict[str, Any]
) -> None:
    sid = glow["services"]["Haircut"]
    await book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30")
    h = auth(glow["token"])
    await client.put(f"/services/{sid}", json={"duration_min": 60}, headers=h)
    appt = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=h)).json()[0]
    assert appt["end_time"] == "2026-10-10T18:00:00+05:30"


async def test_working_hours_replace_and_validate(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    h = auth(glow["token"])
    new = [{"weekday": 0, "open_time": "09:00", "close_time": "12:00"}]
    r = await client.put("/working-hours", json=new, headers=h)
    assert r.status_code == 200
    assert r.json() == [{"weekday": 0, "open_time": "09:00:00", "close_time": "12:00:00"}]

    overlap = [
        {"weekday": 2, "open_time": "10:00", "close_time": "13:00"},
        {"weekday": 2, "open_time": "12:00", "close_time": "15:00"},
    ]
    r = await client.put("/working-hours", json=overlap, headers=h)
    assert r.status_code == 422 and r.json()["error"] == "OVERLAPPING_HOURS"
    reversed_ = [{"weekday": 2, "open_time": "13:00", "close_time": "10:00"}]
    assert (await client.put("/working-hours", json=reversed_, headers=h)).status_code == 422
    # a failed PUT leaves the previous week intact
    assert len((await client.get("/working-hours", headers=h)).json()) == 1


async def test_today_summary_and_stats(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    h = auth(glow["token"])
    s = glow["services"]
    refs = []
    for i, (svc, time_) in enumerate(
        [("Haircut", "10:00"), ("Haircut + Beard", "11:00"), ("Beard Trim", "14:00"), ("Haircut", "15:00")]
    ):
        r = await book(client, "glow-salon", s[svc], f"2026-10-10T{time_}:00+05:30", phone=f"900000000{i}")
        refs.append(r.json()["booking_id"])
    await book(client, "glow-salon", s["Haircut"], "2026-10-13T10:00:00+05:30", phone="9000000009")  # Tuesday

    appts = {
        a["booking_id"]: a["id"]
        for a in (await client.get("/appointments", params={"date": BOOK_DAY}, headers=h)).json()
    }
    await client.patch(f"/appointments/{appts[refs[0]]}", json={"status": "completed"}, headers=h)
    await client.patch(f"/appointments/{appts[refs[1]]}", json={"status": "completed"}, headers=h)
    await client.patch(f"/appointments/{appts[refs[2]]}", json={"status": "no_show"}, headers=h)
    await client.patch(f"/appointments/{appts[refs[3]]}", json={"status": "cancelled"}, headers=h)

    today = (await client.get("/dashboard/today", params={"date": BOOK_DAY}, headers=h)).json()
    assert today == {
        "date": BOOK_DAY,
        "business_name": "Glow Salon",
        "count": 3,
        "no_shows": 1,
        "revenue_estimate": 720.0,
    }

    stats = (await client.get("/stats", params={"month": "2026-10"}, headers=h)).json()
    assert stats == {
        "month": "2026-10",
        "total": 4,
        "completed": 2,
        "no_show": 1,
        "cancelled": 1,
        "no_show_rate": round(1 / 3, 4),
        "revenue_estimate": 720.0,
        "busiest_weekday": "Saturday",
    }
    empty = (await client.get("/stats", params={"month": "2026-11"}, headers=h)).json()
    assert empty["total"] == 0 and empty["no_show_rate"] == 0 and empty["busiest_weekday"] is None
    assert (await client.get("/stats", params={"month": "2026-13"}, headers=h)).status_code == 422
