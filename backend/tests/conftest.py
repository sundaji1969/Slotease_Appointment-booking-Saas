"""Test configuration. Integration tests run against a REAL Postgres test database
(default: the slotease_test DB created by docker compose; override with TEST_DATABASE_URL)."""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://slotease:slotease@localhost:5433/slotease_test"
)
os.environ["JWT_SECRET"] = "test-only-secret-" + "x" * 40
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["RESEND_API_KEY"] = ""

from collections.abc import AsyncIterator, Iterator  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.deps.clock import get_now  # noqa: E402
from app.main import app  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
# Frozen "now": Friday 9 Oct 2026, 10:00 IST. The canonical booking is Sat 10 Oct 17:30.
NOW = datetime(2026, 10, 9, 10, 0, tzinfo=IST)
BOOK_DAY = "2026-10-10"

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_db() -> Iterator[None]:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.sqlalchemy_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_db() -> Iterator[None]:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE businesses CASCADE"))
    yield


@pytest.fixture(autouse=True)
def frozen_clock() -> Iterator[None]:
    app.dependency_overrides[get_now] = lambda: NOW
    yield
    app.dependency_overrides.pop(get_now, None)


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


SALON_HOURS = [
    {"weekday": wd, "open_time": o, "close_time": c}
    for wd in range(1, 7)
    for o, c in (("10:00", "13:00"), ("14:00", "20:00"))
]


async def create_business(
    client: httpx.AsyncClient,
    slug: str,
    name: str = "Glow Salon",
    email: str | None = None,
    services: list[tuple[str, int, int]] | None = None,
    hours: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Register a business through the API and configure services + hours. Returns ids and token."""
    r = await client.post(
        "/auth/register",
        json={
            "business_name": name,
            "slug": slug,
            "email": email or f"owner@{slug}.test",
            "password": "Passw0rd!",
            "phone": "9876543210",
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    svc_ids: dict[str, str] = {}
    for svc_name, dur, price in services or [
        ("Haircut", 30, 300),
        ("Beard Trim", 15, 150),
        ("Haircut + Beard", 45, 420),
    ]:
        rs = await client.post(
            "/services", json={"name": svc_name, "duration_min": dur, "price": price}, headers=auth(token)
        )
        assert rs.status_code == 201, rs.text
        svc_ids[svc_name] = rs.json()["id"]
    rh = await client.put(
        "/working-hours", json=hours if hours is not None else SALON_HOURS, headers=auth(token)
    )
    assert rh.status_code == 200, rh.text
    return {"slug": slug, "token": token, "services": svc_ids, "business": r.json()["business"]}


async def book(
    client: httpx.AsyncClient,
    slug: str,
    service_id: str,
    start: str,
    name: str = "Ravi Kumar",
    phone: str = "9123456780",
) -> httpx.Response:
    return await client.post(
        f"/public/{slug}/bookings",
        json={"service_id": service_id, "start_time": start, "name": name, "phone": phone},
    )


@pytest.fixture
async def glow(client: httpx.AsyncClient) -> dict[str, Any]:
    return await create_business(client, "glow-salon")
