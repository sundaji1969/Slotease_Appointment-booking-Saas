"""R2: Business A cannot read or change Business B's data. Every owner endpoint is covered."""

from typing import Any

import httpx
import pytest

from tests.conftest import BOOK_DAY, auth

Tenants = dict[str, dict[str, Any]]


async def test_a_cannot_patch_b_appointment(client: httpx.AsyncClient, tenants: Tenants) -> None:
    a, b = tenants["A"], tenants["B"]
    r = await client.patch(
        f"/appointments/{b['appointment_id']}", json={"status": "cancelled"}, headers=auth(a["token"])
    )
    assert r.status_code == 404
    # B's appointment is untouched
    b_appts = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=auth(b["token"]))).json()
    assert b_appts[0]["status"] == "booked"


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
async def test_a_cannot_touch_b_service(client: httpx.AsyncClient, tenants: Tenants, method: str) -> None:
    a, b = tenants["A"], tenants["B"]
    sid = b["services"]["Haircut"]
    kwargs: dict[str, Any] = {"headers": auth(a["token"])}
    if method == "PUT":
        kwargs["json"] = {"name": "Hacked", "price": 1}
    r = await client.request(method, f"/services/{sid}", **kwargs)
    assert r.status_code == 404
    assert r.json()["error"] == "SERVICE_NOT_FOUND"
    b_svc = (await client.get(f"/services/{sid}", headers=auth(b["token"]))).json()
    assert b_svc["name"] == "Haircut" and b_svc["is_active"] is True and b_svc["price"] == 300


async def test_lists_never_contain_other_tenant_rows(client: httpx.AsyncClient, tenants: Tenants) -> None:
    a, b = tenants["A"], tenants["B"]
    h = auth(a["token"])
    appts = (
        await client.get("/appointments", params={"from": "2026-10-01", "to": "2026-10-31"}, headers=h)
    ).json()
    assert [x["id"] for x in appts] == [a["appointment_id"]]
    svc_ids = {s["id"] for s in (await client.get("/services", headers=h)).json()}
    assert svc_ids == set(a["services"].values())
    assert not svc_ids & set(b["services"].values())


async def test_stats_and_today_are_per_tenant(client: httpx.AsyncClient, tenants: Tenants) -> None:
    h = auth(tenants["A"]["token"])
    assert (await client.get("/dashboard/today", params={"date": BOOK_DAY}, headers=h)).json()["count"] == 1
    assert (await client.get("/stats", params={"month": "2026-10"}, headers=h)).json()["total"] == 1
    assert (await client.get("/me", headers=h)).json()["slug"] == "biz-a"


async def test_a_replacing_hours_does_not_touch_b(client: httpx.AsyncClient, tenants: Tenants) -> None:
    a, b = tenants["A"], tenants["B"]
    before = (await client.get("/working-hours", headers=auth(b["token"]))).json()
    await client.put("/working-hours", json=[], headers=auth(a["token"]))
    assert (await client.get("/working-hours", headers=auth(a["token"]))).json() == []
    assert (await client.get("/working-hours", headers=auth(b["token"]))).json() == before


async def test_business_id_in_client_payload_is_ignored(client: httpx.AsyncClient, tenants: Tenants) -> None:
    a, b = tenants["A"], tenants["B"]
    r = await client.post(
        "/services",
        json={"name": "Sneaky", "duration_min": 30, "price": 1, "business_id": b["business"]["id"]},
        headers=auth(a["token"]),
    )
    assert r.status_code == 201
    b_names = {s["name"] for s in (await client.get("/services", headers=auth(b["token"]))).json()}
    assert "Sneaky" not in b_names


async def test_public_booking_cannot_use_other_tenant_service(
    client: httpx.AsyncClient, tenants: Tenants
) -> None:
    a, b = tenants["A"], tenants["B"]
    r = await client.post(
        f"/public/{a['slug']}/bookings",
        json={
            "service_id": b["services"]["Haircut"],
            "start_time": "2026-10-10T11:00:00+05:30",
            "name": "X Y",
            "phone": "9000000001",
        },
    )
    assert r.status_code == 404
    r = await client.get(
        f"/public/{a['slug']}/slots", params={"service_id": b["services"]["Haircut"], "date": BOOK_DAY}
    )
    assert r.status_code == 404
