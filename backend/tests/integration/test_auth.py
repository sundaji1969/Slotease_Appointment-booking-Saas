import httpx
import pytest

from tests.conftest import auth


def reg(**overrides: str) -> dict[str, str]:
    body = {
        "business_name": "Glow Salon",
        "slug": "glow-salon",
        "email": "owner@glow.test",
        "password": "Passw0rd!",
        "phone": "9876543210",
    }
    body.update(overrides)
    return body


async def test_health(client: httpx.AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "x-request-id" in r.headers


async def test_register_creates_business_and_returns_token(client: httpx.AsyncClient) -> None:
    r = await client.post("/auth/register", json=reg())
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"]
    assert body["business"]["slug"] == "glow-salon"
    assert body["business"]["phone"] == "+919876543210"
    assert body["business"]["timezone"] == "Asia/Kolkata"
    me = await client.get("/me", headers=auth(body["access_token"]))
    assert me.status_code == 200 and me.json()["name"] == "Glow Salon"


async def test_duplicate_slug_and_email_conflict(client: httpx.AsyncClient) -> None:
    assert (await client.post("/auth/register", json=reg())).status_code == 201
    r = await client.post("/auth/register", json=reg(email="other@glow.test"))
    assert r.status_code == 409 and r.json()["error"] == "SLUG_TAKEN"
    r = await client.post("/auth/register", json=reg(slug="another-slug", email="OWNER@glow.test"))
    assert r.status_code == 409 and r.json()["error"] == "EMAIL_TAKEN"  # citext: case-insensitive


@pytest.mark.parametrize("slug", ["ab", "Has Caps!", "dashboard", "login", "x" * 41, "under_score"])
async def test_invalid_or_reserved_slug_rejected(client: httpx.AsyncClient, slug: str) -> None:
    r = await client.post("/auth/register", json=reg(slug=slug))
    assert r.status_code == 422
    assert r.json()["error"] == "VALIDATION_ERROR"
    assert set(r.json()) == {"error", "message"}


async def test_short_password_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post("/auth/register", json=reg(password="short"))
    assert r.status_code == 422


async def test_login_happy_and_generic_failures(client: httpx.AsyncClient) -> None:
    await client.post("/auth/register", json=reg())
    ok = await client.post("/auth/login", json={"email": "owner@glow.test", "password": "Passw0rd!"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad_pw = await client.post("/auth/login", json={"email": "owner@glow.test", "password": "nope-nope"})
    no_user = await client.post("/auth/login", json={"email": "ghost@glow.test", "password": "Passw0rd!"})
    assert bad_pw.status_code == no_user.status_code == 401
    assert bad_pw.json() == no_user.json()  # no user enumeration


async def test_owner_endpoints_need_valid_token(client: httpx.AsyncClient) -> None:
    assert (await client.get("/services")).status_code == 401
    r = await client.get("/services", headers=auth("not-a-jwt"))
    assert r.status_code == 401 and r.json()["error"] == "INVALID_TOKEN"
