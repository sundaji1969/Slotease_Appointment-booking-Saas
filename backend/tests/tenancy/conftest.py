"""Business A and Business B, each with services, hours and one booking. Reused by tenancy tests."""

from typing import Any

import httpx
import pytest

from tests.conftest import BOOK_DAY, auth, book, create_business


@pytest.fixture
async def tenants(client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    a = await create_business(client, "biz-a", name="Business A")
    b = await create_business(client, "biz-b", name="Business B")
    for t in (a, b):
        r = await book(client, t["slug"], t["services"]["Haircut"], "2026-10-10T17:30:00+05:30")
        assert r.status_code == 201
        appts = (
            await client.get("/appointments", params={"date": BOOK_DAY}, headers=auth(t["token"]))
        ).json()
        t["appointment_id"] = appts[0]["id"]
    return {"A": a, "B": b}
