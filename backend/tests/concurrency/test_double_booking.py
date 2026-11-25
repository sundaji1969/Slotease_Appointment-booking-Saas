"""R1: two people booking the same slot at the same moment -> exactly one 201, the rest 409.

Requests go through the ASGI app concurrently; sync endpoints run in FastAPI's threadpool, each with its
own pooled DB connection, so the database (not Python) decides the winner.
"""

import asyncio
from collections import Counter
from typing import Any

import httpx

from tests.conftest import BOOK_DAY, auth, book


async def test_ten_parallel_bookings_one_wins(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    sid = glow["services"]["Haircut"]
    results = await asyncio.gather(
        *(
            book(client, "glow-salon", sid, "2026-10-10T17:30:00+05:30", phone=f"90000000{i:02d}")
            for i in range(10)
        )
    )
    codes = Counter(r.status_code for r in results)
    assert codes == {201: 1, 409: 9}, codes
    assert all(r.json()["error"] == "SLOT_TAKEN" for r in results if r.status_code == 409)
    appts = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=auth(glow["token"]))).json()
    assert len(appts) == 1


async def test_parallel_overlapping_different_starts_one_wins(
    client: httpx.AsyncClient, glow: dict[str, Any]
) -> None:
    s = glow["services"]
    results = await asyncio.gather(
        book(client, "glow-salon", s["Haircut + Beard"], "2026-10-10T17:30:00+05:30", phone="9000000001"),
        book(client, "glow-salon", s["Haircut"], "2026-10-10T17:45:00+05:30", phone="9000000002"),
        book(client, "glow-salon", s["Haircut"], "2026-10-10T18:00:00+05:30", phone="9000000003"),
    )
    # 17:30-18:15, 17:45-18:15 and 18:00-18:30 all overlap pairwise -> exactly one can win.
    codes = Counter(r.status_code for r in results)
    assert codes == {201: 1, 409: 2}, codes
    appts = (await client.get("/appointments", params={"date": BOOK_DAY}, headers=auth(glow["token"]))).json()
    spans = sorted((a["start_time"], a["end_time"]) for a in appts)
    for (_, end_a), (start_b, _) in zip(spans, spans[1:], strict=False):
        assert end_a <= start_b, f"overlap slipped through: {spans}"


async def test_overlap_45_then_30_is_409(client: httpx.AsyncClient, glow: dict[str, Any]) -> None:
    s = glow["services"]
    first = await book(client, "glow-salon", s["Haircut + Beard"], "2026-10-10T17:30:00+05:30")
    assert first.status_code == 201
    second = await book(client, "glow-salon", s["Haircut"], "2026-10-10T17:45:00+05:30", phone="9000000002")
    assert second.status_code == 409
    assert second.json()["error"] == "SLOT_TAKEN"
