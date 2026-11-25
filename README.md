# SlotEase — appointment booking for clinics, salons & physio centres

Multi-tenant MicroSaaS (₹499/month per business). Each business gets:

- **A public, mobile-first booking page** at `/{slug}`: pick a service, day and time, enter name and phone, and you're booked in about 30 seconds.
- **An owner dashboard** with today's schedule and status buttons, a weekly calendar, services, working hours, monthly stats, and a share link.
- **A hard guarantee:** the database itself makes double booking impossible.

| | URL |
|---|---|
| Live app | https://slotease.sundajigenai.tech (demo: [/glow-salon](https://slotease.sundajigenai.tech/glow-salon)) |
| API | https://slotease.sundajigenai.tech/api (health: `/api/health`) |

Screenshots: _booking page (mobile)_ · _dashboard_ · _409 demo_ (add yours here)

## Stack

React 18 + Vite + TypeScript + Tailwind · TanStack Query · React Hook Form + Zod ·
FastAPI (Python 3.12) · SQLAlchemy 2 · Pydantic v2 · Alembic · PostgreSQL 16 · JWT + bcrypt ·
pytest · Vitest + MSW · Playwright.

## Local setup (≈10 minutes)

Prerequisites: Docker, Python 3.12, Node 20+.

```bash
cp .env.example .env                 # then set JWT_SECRET (see the comment in the file)
docker compose up -d db              # Postgres 16 on localhost:5433 (+ slotease_test DB)

cd backend
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m scripts.seed               # demo data, see below
uvicorn app.main:app --reload --port 8000

cd ../frontend
cp .env.example .env                 # VITE_API_URL=http://localhost:8000
npm install
npm run dev                          # http://localhost:5173
```

Demo accounts (password `Passw0rd!`): `owner@glow.test` (page `/glow-salon`) and `owner@carephysio.test` (page `/care-physio`).

If port 5432/8000 is already in use on your machine, set `DB_PORT` / `API_PORT` in `.env`. The DB defaults to 5433.
Running everything in Docker also works: `docker compose up --build`. The API container runs migrations on start.

## Database (6 tables)

| Table | Key columns | Notes |
|---|---|---|
| `businesses` | id, name, **slug** (unique), phone, timezone (`Asia/Kolkata`), slot_step_min (15), plan | the tenant |
| `users` | id, business_id → businesses, email (CITEXT, unique), password_hash (bcrypt), role | owner/staff |
| `services` | id, business_id, name, duration_min (5–480), price ≥ 0, is_active | DELETE = soft delete |
| `working_hours` | id, business_id, weekday (0 = Mon), open_time, close_time | several rows per day = lunch breaks |
| `customers` | id, business_id, name, phone (E.164) | UNIQUE (business_id, phone) → repeat-visit history |
| `appointments` | id, public_ref (`APT-YYYYMMDD-NNNN`), business_id, service_id, customer_id, start_time, end_time (TIMESTAMPTZ), status | `booked / completed / cancelled / no_show` |

All child tables use `ON DELETE CASCADE` from `businesses`. Times are stored in UTC and computed and returned in the business timezone (ISO 8601 with offset).

### How double booking is prevented

A `UNIQUE (business_id, start_time)` alone is **not enough**. A 45-minute booking at 17:30 and a 30-minute booking at 17:45 have different start times but overlap. The migration (`backend/alembic/versions/0001_initial_schema.py`) adds a PostgreSQL **exclusion constraint**:

```sql
ALTER TABLE appointments ADD CONSTRAINT no_overlapping_appointments
  EXCLUDE USING gist (business_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&)
  WHERE (status IN ('booked','completed'));
```

- `[)` (half-open ranges) means back-to-back bookings such as 17:00–17:30 and 17:30–18:00 are allowed.
- Cancelled and no-show rows are ignored, so a freed slot can be booked again.
- The brief's `UNIQUE (business_id, start_time)` is kept as a partial unique index with the same `WHERE`.
- The API never does "check, then insert". It inserts, and Postgres decides who wins. The `IntegrityError` is translated to **409 `SLOT_TAKEN`**. The free-slot list is only a hint for the UI.

### How tenancy is enforced

- The `business_id` comes **only from the verified JWT** (`deps/tenant.py → TenantContext`). Owner endpoints have no `business_id` parameter, and one sent in a request body is ignored.
- Every repository function takes `business_id` as a required argument and filters through `scoped()`. Joins are tenant-filtered too.
- Accessing another tenant's ID returns **404**, not 403, so IDs can't be probed.

## API

Every error uses the same shape: `{"error": "CODE", "message": "Human readable"}`. Interactive docs are at `/docs`.

| Method + path | Auth | Purpose |
|---|---|---|
| `POST /auth/register` | — | business + owner in one transaction → `{access_token, business}` (409 slug/email taken) |
| `POST /auth/login` | — | → `{access_token}` / 401 |
| `GET /public/{slug}` | — | name, phone, timezone |
| `GET /public/{slug}/services` | — | active services |
| `GET /public/{slug}/slots?service_id&date` | — | `{date, slots: [iso…]}` |
| `POST /public/{slug}/bookings` | — | 201 booking · 409 `SLOT_TAKEN` · 422 `OFF_GRID`/`OUTSIDE_HOURS`/`TOO_SOON` |
| `GET /me` | JWT | logged-in business |
| `GET /appointments?date=` or `?from&to` (`limit≤200`, `offset`) | JWT | list joined with customer + service |
| `PATCH /appointments/{id}` `{status}` | JWT | booked → completed/cancelled/no_show; terminal = 422 |
| `GET/POST /services`, `GET/PUT/DELETE /services/{id}` | JWT | CRUD, DELETE deactivates |
| `GET/PUT /working-hours` | JWT | PUT replaces the whole week atomically |
| `GET /dashboard/today?date=` | JWT | count, no-shows, revenue estimate |
| `GET /stats?month=YYYY-MM` | JWT | total, completed, no_show, no_show_rate, revenue_estimate, busiest_weekday |

Rate limits: `/auth/*` 5/min, public bookings 10/min per IP.

**201 example**

```http
POST /public/glow-salon/bookings
{"service_id":"…","start_time":"2026-10-10T17:30:00+05:30","name":"Ravi Kumar","phone":"9876543210"}

HTTP/1.1 201 Created
{
  "booking_id": "APT-20261010-0007",
  "service": "Haircut + Beard",
  "start_time": "2026-10-10T17:30:00+05:30",
  "end_time": "2026-10-10T18:15:00+05:30",
  "status": "booked",
  "message": "Booking confirmed at Glow Salon, Sat 10 Oct, 5:30 PM"
}
```

**409 example** (same or overlapping slot)

```http
HTTP/1.1 409 Conflict
{"error": "SLOT_TAKEN", "message": "This slot was just booked. Please pick another time."}
```

**Booking assistant (optional, OpenAI):** set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`) and a "Just tell us what you need" box appears on the booking page. A customer types e.g. *"haircut Saturday evening"* and taps one of the suggested times. The model only extracts the service, day and time of day as strict JSON, and every value is validated (the service must belong to this business, the date must be inside the booking window). The suggested times come from the same slot engine as the rest of the page, so the AI can't invent availability or bypass the double-booking constraint. Endpoint: `POST /public/{slug}/assistant` `{message, history?}` → `{reply, service_id, date, slots}` (10/min per IP; 503 `ASSISTANT_UNAVAILABLE` without a key).

Notifications: the owner gets an email via Resend (when `RESEND_API_KEY` is set; otherwise it is logged) from a background task. A failed email never fails a booking. Dashboard rows have a one-tap WhatsApp confirmation link (`wa.me`).

## Tests

```bash
cd backend  && ruff check . && mypy app && pytest -q --cov=app/services --cov=app/repositories
cd frontend && npm run lint && npm test -- --run && npm run build
cd frontend && npx playwright install chromium && npm run e2e   # needs the API running
```

| Suite | What it proves |
|---|---|
| `tests/unit/test_slots.py` | slot engine: open/close edges, lunch break, duration vs close, back-to-back, overlaps, lead time, past/60-day limits, IST offset, 15 vs 30 step |
| `tests/integration/test_constraints.py` | the DB rejects same-start and overlapping bookings, allows back-to-back, cancelled re-booking, and the same slot in two businesses |
| `tests/concurrency/test_double_booking.py` | 10 parallel POSTs for one slot → exactly 1×201 + 9×409; 45-min 17:30 then 17:45 → 409 |
| `tests/tenancy/test_isolation.py` | with A's token, every B resource → 404; lists never contain B rows |
| `tests/integration/test_*` | auth, booking happy path matches the brief byte-for-byte, owner APIs, stats, notifications |
| `frontend/tests/*` | booking flow, 409 toast + slot refetch, validation, optimistic status update + rollback, hours form |
| `frontend/e2e/booking.spec.ts` | register → service → hours → book on a 390×844 phone → dashboard → complete; two phones racing for one slot |

## Done checklist

- [x] Two browsers book the same slot → one 201, one 409: EXCLUDE + partial UNIQUE (migration 0001), `tests/concurrency`, Playwright race test
- [x] Business A can't touch Business B data: `TenantContext` + `scoped()` repositories, `tests/tenancy`
- [x] Slots respect working hours, duration and existing bookings: `services/slots.py`, `tests/unit/test_slots.py`
- [x] Booking page works on mobile: 360px layout, 48px tap targets, sticky confirm, Playwright mobile viewport
- [x] Hashed passwords (bcrypt, cost 12), secrets in `.env` (`.env.example` committed), live URL: https://slotease.sundajigenai.tech
- [x] README covers setup, DB tables and API endpoints

## Deploy (Phase 10)

1. **Neon:** create a database, then run `CREATE EXTENSION btree_gist; CREATE EXTENSION citext;` (the migration also tries this). Copy the connection string.
2. **Render:** New → Web Service → Docker, root `backend/`. Set the env vars from `.env.example` (`DATABASE_URL` = Neon URL, a strong `JWT_SECRET`, `CORS_ORIGINS` = your Vercel URL, `APP_BASE_URL`, optional `RESEND_API_KEY`). Health check path: `/health`. The container runs `alembic upgrade head` and then uvicorn on `$PORT`.
3. **Vercel:** import `frontend/` and set `VITE_API_URL` = Render URL. `vercel.json` rewrites every path to `index.html`, so `/glow-salon` works on refresh.
4. Update `CORS_ORIGINS` on Render to the final Vercel URL.

### Self-hosting on a VPS (Docker)

Everything is served on one port through nginx: `/` is the app and `/api` is the API. The database and API ports are not exposed.

```bash
git clone https://github.com/sundaji1969/Slotease_Appointment-booking-Saas.git slotease && cd slotease
cp .env.prod.example .env.prod   # set POSTGRES_PASSWORD, JWT_SECRET, CORS_ORIGINS/APP_BASE_URL=http://SERVER_IP:8080, OPENAI_API_KEY
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod exec api python -m scripts.seed   # optional demo data
```

Open `http://SERVER_IP:8080/glow-salon`. Allow the port in the firewall if needed (`ufw allow 8080/tcp`).
To update: `git pull && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`.

## Claude Code setup

`CLAUDE.md` (project rules), `.claude/settings.json` (permissions and the ruff hook), `.claude/commands/{phase,verify,tenant-audit}.md`, and `.claude/agents/{security-reviewer,test-writer}.md` come from the guide in `docs/GUIDE.md`.
