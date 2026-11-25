
SlotEase — Claude Code Development Guide & Master Prompt
Use Case 04 · MicroSaaS Track · Social Eagle AI Academy (Intermediate)
Product: Multi-tenant appointment booking SaaS for clinics, salons and physiotherapy centres
Business model: ₹499 / month per business · Build time: 4–5 days
Author role: Gen AI Solution Architect · Version: 1.0 · November 2026

Contents

0. How to Use This Guide
This document has three parts:
Part
What it is
When you use it
A. Architecture Blueprint
The design decisions, data model, slot algorithm, concurrency and tenancy rules
Read once before you start; Claude Code reads it via CLAUDE.md
B. Claude Code Setup
Repo scaffolding, CLAUDE.md, custom slash commands, sub-agents, permissions, hooks
Day 0 — 30 minutes
C. Phase-by-Phase Prompts
Copy-paste prompts, one per phase, each with acceptance criteria
Day 1 to Day 5

Golden rule for working with Claude Code: one phase per session, plan first, tests before "done", commit after every green phase. Never ask Claude Code to "build the whole app" in one prompt — you'll get a big, unreviewable diff.


PART A — ARCHITECTURE BLUEPRINT
A1. Problem Recap
Small businesses take bookings by phone and WhatsApp. Results: double bookings, forgotten appointments, no record of no-shows. SlotEase gives each business:
A public, mobile-first booking page — slotease.app/{slug} — book in 30 seconds.
An owner dashboard — today's schedule, weekly calendar, services, working hours, status buttons, stats.
A hard guarantee — the database itself makes double booking impossible.
A2. Non-Negotiable Requirements (from the brief's Done Checklist)
#
Requirement
How we prove it
R1
Two browsers booking the same slot concurrently → one 201, one 409 SLOT_TAKEN
Automated concurrency test (pytest + asyncio.gather) and a manual demo
R2
Business A cannot read or change Business B's data
Automated cross-tenant test suite for every owner endpoint
R3
Slots respect working hours, service duration and existing bookings
Unit tests on the pure slot function
R4
Booking page works on mobile
Tested at 360px width; Lighthouse mobile score ≥ 90
R5
Hashed passwords, secrets in .env, live deployed URL
bcrypt, .env.example, Vercel + Render URLs in README
R6
README covers setup, DB tables, API endpoints
README checklist in Phase 8

A3. Technology Stack (locked decisions)
Layer
Choice
Why
Frontend
React 18 + Vite + TypeScript + Tailwind CSS
Fast dev loop, small bundle, mobile-first utility CSS
Data fetching
TanStack Query + Axios
Caching, refetch on 409, loading states for free
Forms
React Hook Form + Zod
Same validation shape as backend
Backend
FastAPI (Python 3.12) + SQLAlchemy 2.0 + Pydantic v2
Typed, auto OpenAPI docs at /docs
Migrations
Alembic
Versioned schema; the constraints live in migrations
Database
PostgreSQL 16 (Neon or Supabase free tier)
Supports EXCLUDE constraints and tstzrange
Auth
JWT (access token, 60 min) + bcrypt via passlib
Matches the brief
Notifications
Resend (email) + WhatsApp click-to-chat link (wa.me)
Free tier, no WhatsApp Business approval needed
Tests
pytest + httpx AsyncClient (backend), Vitest + Testing Library (frontend), Playwright (one E2E)
Deploy
Frontend → Vercel · Backend → Render (Docker) · DB → Neon
All free tiers
Local dev
Docker Compose (postgres + api)
One command to run

A4. System Architecture
┌──────────────────────┐        HTTPS/JSON        ┌───────────────────────────┐
│  React SPA (Vercel)  │ ───────────────────────▶ │  FastAPI (Render, Docker) │
│                      │                          │                           │
│  /:slug   (public)   │   GET  /public/{slug}/…  │  routers/public.py        │
│  /login   /register  │   POST /auth/…           │  routers/auth.py          │
│  /dashboard/* (JWT)  │   GET  /appointments …   │  routers/owner/*.py       │
└──────────────────────┘                          │  services/slots.py (pure) │
                                                  │  services/booking.py      │
                                                  │  services/notify.py       │
                                                  │  deps/tenant.py ◀── JWT   │
                                                  └────────────┬──────────────┘
                                                               │ SQLAlchemy
                                                               ▼
                                                  ┌───────────────────────────┐
                                                  │ PostgreSQL (Neon)         │
                                                  │ 6 tables + EXCLUDE/UNIQUE │
                                                  └───────────────────────────┘
Layering rule: routers are thin (parse → call service → return). Business logic lives in services/. Database access lives in repositories/ and every repository function takes business_id as a required argument.
A5. Database Design
Six tables from the brief, with the architect's additions marked ★.
-- businesses (tenants)
id UUID PK, name TEXT, slug TEXT UNIQUE NOT NULL, phone TEXT,
timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',          -- ★
slot_step_min INT NOT NULL DEFAULT 15,                  -- ★ slot grid granularity
plan TEXT NOT NULL DEFAULT 'trial', created_at TIMESTAMPTZ DEFAULT now()
 
-- users
id UUID PK, business_id UUID FK → businesses ON DELETE CASCADE,
email CITEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
role TEXT CHECK (role IN ('owner','staff')), created_at TIMESTAMPTZ
 
-- services
id UUID PK, business_id UUID FK, name TEXT, duration_min INT CHECK (duration_min BETWEEN 5 AND 480),
price NUMERIC(10,2) CHECK (price >= 0), is_active BOOL DEFAULT true   -- ★ soft delete
 
-- working_hours
id UUID PK, business_id UUID FK, weekday SMALLINT CHECK (weekday BETWEEN 0 AND 6),  -- 0 = Monday
open_time TIME, close_time TIME, CHECK (close_time > open_time)
-- multiple rows per weekday allowed → supports lunch breaks (10:00–13:00, 14:00–20:00)
 
-- customers
id UUID PK, business_id UUID FK, name TEXT, phone TEXT,
UNIQUE (business_id, phone)                                            -- ★ repeat-visit history
 
-- appointments
id UUID PK, public_ref TEXT UNIQUE,                                    -- ★ "APT-20261010-0007"
business_id UUID FK, service_id UUID FK, customer_id UUID FK,
start_time TIMESTAMPTZ, end_time TIMESTAMPTZ, CHECK (end_time > start_time),
status TEXT CHECK (status IN ('booked','completed','cancelled','no_show')) DEFAULT 'booked',
created_at TIMESTAMPTZ DEFAULT now()
A5.1 The double-booking guarantee (critical architect note)
The brief asks for UNIQUE (business_id, start_time). Keep it — but it is not enough on its own. It only blocks two bookings that start at the *exact same minute*. With variable service durations it misses overlaps:
Haircut + Beard 17:30–18:15 is booked. A second customer books a Haircut at 17:45. Different start_time → the UNIQUE rule allows it → double booking.
Fix: add a PostgreSQL exclusion constraint on the time range, limited to active appointments:
CREATE EXTENSION IF NOT EXISTS btree_gist;
 
ALTER TABLE appointments
  ADD CONSTRAINT no_overlapping_appointments
  EXCLUDE USING gist (
    business_id WITH =,
    tstzrange(start_time, end_time, '[)') WITH &&
  ) WHERE (status IN ('booked','completed'));
'[)' means a 17:00–17:30 booking and a 17:30–18:00 booking do not clash (back-to-back is fine).
Cancelled and no-show rows are excluded, so a cancelled slot can be re-booked.
Keep the brief's UNIQUE (business_id, start_time) as a partial unique index with the same WHERE clause, so the checklist item is visibly satisfied and cancelled slots can still be re-booked.
When the multi-staff stretch goal is added, replace business_id WITH = with staff_id WITH =.
A5.2 Indexes
CREATE INDEX ix_appt_business_start ON appointments (business_id, start_time);
CREATE INDEX ix_services_business ON services (business_id) WHERE is_active;
CREATE INDEX ix_hours_business_weekday ON working_hours (business_id, weekday);
A6. Slot Calculation Algorithm
Implemented as a pure function in services/slots.py with no database access, so it can be unit-tested exhaustively.
compute_free_slots(
    date, tz, working_windows: list[(open, close)],
    busy: list[(start, end)], duration_min, step_min, now, lead_time_min=30
) -> list[datetime]
 
1. For each working window on that weekday:
     t = window.open
     while t + duration <= window.close:
         candidate = [t, t + duration)
         if candidate.start >= now + lead_time
            and candidate overlaps no busy interval:
              yield t
         t += step_min
2. Return the sorted, de-duplicated list in the business's timezone (ISO 8601 with offset).
Rules:
Overlap test: a.start < b.end and b.start < a.end (half-open intervals).
busy = appointments with status booked or completed that day.
Work in the business timezone (zoneinfo.ZoneInfo); store in UTC (TIMESTAMPTZ).
Reject dates in the past and more than 60 days ahead.
The slot list is a hint, never the guarantee. The guarantee is the DB constraint at insert time.
A7. Booking Flow & Concurrency
POST /public/{slug}/bookings  {service_id, start_time, name, phone}
 
1. Resolve business by slug (404 if missing).
2. Load service — must belong to this business and be active (404 otherwise).
3. end_time = start_time + duration.
4. Re-validate: start_time falls inside working hours and on the slot grid (422 otherwise).
5. BEGIN
     upsert customer (business_id, phone)
     INSERT appointment
   COMMIT
6. On IntegrityError for constraint `no_overlapping_appointments` or the unique index
     → ROLLBACK → 409 {"error":"SLOT_TAKEN","message":"This slot was just booked. Please pick another time."}
7. On success → 201 with booking payload → enqueue notification (FastAPI BackgroundTasks).
Do not do "SELECT to check, then INSERT" as the protection — that has a race window. Let the database decide; translate its error into a 409.
A8. Multi-Tenancy & Security
Control
Implementation
Tenant from token, never from client
JWT payload: {sub: user_id, bid: business_id, role}. Owner endpoints take no business_id parameter.
Single dependency
get_current_tenant() in deps/tenant.py decodes JWT, returns TenantContext(user_id, business_id, role)
Repository enforcement
Every repository function signature: def get_appointment(db, business_id, appointment_id). Query always includes WHERE business_id = :bid.
Not-found, not forbidden
Accessing another tenant's ID returns 404, so IDs can't be probed
Defense in depth (optional)
PostgreSQL Row-Level Security with SET app.business_id per request
Passwords
bcrypt, cost 12; min length 8
Secrets
.env (gitignored) + .env.example committed; pydantic-settings loads them
CORS
Allow only the Vercel origin + localhost
Rate limiting
slowapi on /auth/* (5/min) and public bookings (10/min per IP)
Input
Pydantic schemas; phone normalised to E.164 (+91…); slug ^[a-z0-9-]{3,40}$

A9. API Contract
Method + path
Auth
Request
Responses
POST /auth/register
—
business_name, slug, email, password, phone
201 {access_token, business} · 409 slug/email taken
POST /auth/login
—
email, password
200 {access_token} · 401
GET /public/{slug}
—
—
200 business name, phone, timezone
GET /public/{slug}/services
—
—
200 active services
GET /public/{slug}/slots?service_id&date
—
—
200 {date, slots:[iso…]}
POST /public/{slug}/bookings
—
service_id, start_time, name, phone
201 booking · 409 SLOT_TAKEN · 422
GET /appointments?date=YYYY-MM-DD
JWT
—
200 list (joined with customer + service)
GET /appointments?from&to
JWT
—
200 list for weekly calendar
PATCH /appointments/{id}
JWT
{status}
200 · 404 · 422 invalid transition
GET/POST/PUT/DELETE /services[/{id}]
JWT
name, duration_min, price
CRUD (DELETE = soft delete)
GET/PUT /working-hours
JWT
list of {weekday, open_time, close_time}
Replace whole week atomically
GET /stats?month=YYYY-MM
JWT
—
{total, completed, no_show, no_show_rate, revenue_estimate, busiest_weekday}

Status transitions: booked → completed | cancelled | no_show. Terminal states can't change (422).
Error envelope (always): {"error": "CODE", "message": "Human readable"}.
Sample success (must match the brief):
HTTP 201 Created
{
  "booking_id": "APT-20261010-0007",
  "service": "Haircut + Beard",
  "start_time": "2026-10-10T17:30:00+05:30",
  "end_time": "2026-10-10T18:15:00+05:30",
  "status": "booked",
  "message": "Booking confirmed at Glow Salon, Sat 10 Oct, 5:30 PM"
}
A10. Repository Structure
slotease/
├── CLAUDE.md                     # Claude Code project memory (Part B)
├── README.md
├── docker-compose.yml
├── .env.example
├── .claude/
│   ├── settings.json             # permissions + hooks
│   ├── commands/                 # custom slash commands
│   │   ├── phase.md
│   │   ├── tenant-audit.md
│   │   └── verify.md
│   └── agents/
│       ├── security-reviewer.md
│       └── test-writer.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml / requirements.txt
│   ├── alembic/ (versions/…)
│   ├── app/
│   │   ├── main.py  config.py  db.py
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic
│   │   ├── repositories/  # all DB access, business_id required
│   │   ├── services/      # slots.py booking.py stats.py notify.py
│   │   ├── routers/       # auth.py public.py owner/{appointments,services,hours,stats}.py
│   │   ├── deps/          # tenant.py db.py
│   │   └── core/          # security.py errors.py
│   ├── scripts/seed.py
│   └── tests/ (unit/ integration/ concurrency/ tenancy/)
└── frontend/
    ├── src/
    │   ├── api/  hooks/  components/  lib/
    │   ├── pages/public/BookingPage.tsx
    │   ├── pages/auth/{Login,Register}.tsx
    │   └── pages/dashboard/{Today,Week,Services,Hours,Stats}.tsx
    └── tests/ + e2e/
A11. Frontend Screens
Public booking (/:slug) — 4 steps, one screen, mobile-first:
Service cards (name · duration · ₹price)
Date strip (next 14 days, horizontal scroll)
Slot grid (chips; disabled while loading; empty state "No free slots — try another day")
Name + phone → Confirm (sticky bottom button, ≥ 48px tap target)
   → Success screen: booking ref, date/time, "Add to WhatsApp" link, "Book another".
   → On 409: toast "This slot was just booked", auto-refetch slots, keep form data.
Owner dashboard (/dashboard):
Today: header GLOW SALON | Today, Sat 10 Oct · 12 bookings · 2 no-shows · Est. ₹6,450; table Time / Customer / Service / Status with [Complete] [No-show] buttons (optimistic update).
Week: 7-column calendar, blocks sized by duration.
Services: list + add/edit modal; deactivate instead of delete.
Working hours: per-weekday rows, add break, "Closed" toggle.
Stats: month picker; total, no-show rate, revenue estimate (completed × price), busiest day.
Share link card: copy slotease.app/{slug} + WhatsApp share button.
A12. Testing Strategy
Layer
Must-have tests
Unit — slots.py
open/close edges; lunch break; duration not fitting before close; back-to-back booking; overlapping busy; lead time; past date; DST-free IST; 15 vs 30 step
Integration — API
register/login; CRUD services; working hours replace; booking happy path; 422 off-grid time; status transitions
Concurrency
10 parallel POSTs for one slot → exactly 1×201 and 9×409. Overlap case: 17:30 (45 min) then 17:45 (30 min) → 409
Tenancy
Create Business A + B. With A's token, GET/PATCH/DELETE every B resource → 404; lists never contain B rows
Frontend
BookingPage flow with mocked API; 409 toast + refetch
E2E (Playwright)
Register → add service → set hours → open public page on mobile viewport → book → see it on dashboard → mark completed

Coverage target: ≥ 85% on services/ and repositories/.


PART B — CLAUDE CODE SETUP (Day 0)
B1. Install & start
mkdir slotease && cd slotease && git init
# Put this guide in the repo as docs/GUIDE.md
claude            # start Claude Code in the repo
Inside Claude Code, run /init once, then replace the generated CLAUDE.md with the one below.
B2. CLAUDE.md (project memory — paste verbatim)
# SlotEase — Project Memory
 
## What this is
Multi-tenant appointment booking SaaS (clinics, salons). Public booking page per business at /{slug};
owner dashboard behind JWT. Full spec: docs/GUIDE.md (Part A is the source of truth).
 
## Stack
- backend/: FastAPI, Python 3.12, SQLAlchemy 2.0 (typed `Mapped[]`), Pydantic v2, Alembic, PostgreSQL 16
- frontend/: React 18 + Vite + TypeScript + Tailwind, TanStack Query, React Hook Form + Zod
- Local: `docker compose up -d db` then run api/web natively
 
## Commands
- Backend tests: `cd backend && pytest -q`
- Backend lint/type: `cd backend && ruff check . && ruff format --check . && mypy app`
- Migrations: `cd backend && alembic revision --autogenerate -m "<msg>" && alembic upgrade head`
- Frontend: `cd frontend && npm run dev | npm test | npm run lint | npm run build`
 
## NON-NEGOTIABLE RULES
1. TENANCY: owner endpoints NEVER accept business_id from the client. Get it from
   `TenantContext` (deps/tenant.py). Every repository function takes `business_id` as a required arg
   and filters by it. Cross-tenant access returns 404.
2. DOUBLE BOOKING: protection is the DB constraint `no_overlapping_appointments` (EXCLUDE USING gist)
   + partial unique (business_id, start_time). Never rely on check-then-insert. Map IntegrityError → 409 SLOT_TAKEN.
3. TIME: store UTC (TIMESTAMPTZ); compute slots in business timezone (default Asia/Kolkata);
   API returns ISO 8601 with offset.
4. slots.py is PURE (no DB, no now() inside — inject `now`).
5. SECRETS: only via pydantic-settings from .env. Never hard-code; never commit .env.
6. ERRORS: always `{"error": CODE, "message": text}`.
7. Routers thin, logic in services/, SQL in repositories/.
8. Every feature ships with tests. A phase is done only when `/verify` passes.
 
## Working style
- Start each phase in Plan Mode; wait for my approval before editing.
- Small commits: `feat(scope): …`, `fix(scope): …`, `test(scope): …`.
- If the spec is ambiguous, ask — don't invent features.
- Do not add new dependencies without saying why.
B3. .claude/settings.json — permissions and hooks
{
  "permissions": {
    "allow": [
      "Bash(pytest:*)", "Bash(ruff:*)", "Bash(mypy:*)", "Bash(alembic:*)",
      "Bash(npm run:*)", "Bash(npm test:*)", "Bash(npx playwright:*)",
      "Bash(docker compose:*)", "Bash(git status)", "Bash(git diff:*)",
      "Bash(git add:*)", "Bash(git commit:*)"
    ],
    "deny": [
      "Read(./.env)", "Read(./**/.env)", "Bash(git push:*)", "Bash(rm -rf:*)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command",
            "command": "cd backend 2>/dev/null && ruff format -q . || true" }
        ]
      }
    ]
  }
}
Denying Read(.env) keeps real secrets out of the model's context. git push stays manual — you review before shipping.
B4. Custom slash commands (.claude/commands/)
phase.md — runs one build phase
Read docs/GUIDE.md Part C, section for phase $ARGUMENTS.
1. Enter plan mode. List files to create/modify, migrations, and tests.
2. Wait for my approval.
3. Implement. Write tests first for services/ and repositories/.
4. Run /verify. Fix until green.
5. Summarise what changed and propose a commit message.
verify.md — the definition of done
Run in order and report pass/fail for each, fixing failures before reporting:
1. cd backend && ruff check . && mypy app && pytest -q
2. cd frontend && npm run lint && npm test -- --run && npm run build
3. grep the backend for any repository function missing a business_id parameter and report it.
4. grep for hard-coded secrets (API keys, passwords, DATABASE_URL literals).
tenant-audit.md
Use the security-reviewer subagent. Audit every router under backend/app/routers/owner and every
repository. For each endpoint confirm: tenant comes from TenantContext, query filters by business_id,
cross-tenant access → 404, and a test exists in tests/tenancy. Output a table: endpoint | ok? | evidence | fix.
B5. Sub-agents (.claude/agents/)
security-reviewer.md
---
name: security-reviewer
description: Reviews SlotEase code for tenant isolation, auth, secrets and injection issues. Use after any backend change.
tools: Read, Grep, Glob, Bash
---
You are a senior application-security reviewer for a multi-tenant SaaS. You did NOT write this code.
Check: business_id isolation on every query, JWT validation and expiry, bcrypt usage, CORS, rate limits,
IntegrityError → 409 mapping, no secrets in code, Pydantic validation on every input.
Report findings ranked Critical/High/Medium/Low with file:line and a concrete fix. Do not edit files.
test-writer.md
---
name: test-writer
description: Writes pytest/Vitest tests from the spec, including edge cases, concurrency and tenancy tests.
tools: Read, Write, Edit, Bash, Grep, Glob
---
Write tests from docs/GUIDE.md section A12 and the acceptance criteria of the current phase.
Prefer behaviour tests over implementation tests. Every test must fail on a plausible bug.
Run them and report results.
B6. Optional MCP servers
MCP
Use
PostgreSQL MCP (read-only, dev DB)
Let Claude inspect schema/constraints while debugging
Playwright MCP
Let Claude drive the browser to check the mobile booking page
GitHub MCP
Open PRs per phase

Connect them with claude mcp add … per each server's own docs. Use a read-only DB role.
B7. Daily Claude Code workflow
claude → /phase N → review the plan (Plan Mode: Shift+Tab to toggle) → approve.
Let it implement; interrupt with Esc if it drifts.
/verify → green.
/tenant-audit after any backend phase.
Review git diff, commit, /clear before the next phase to keep context lean.
Use # to add a new rule to CLAUDE.md whenever you correct Claude twice on the same thing.


PART C — PHASE-BY-PHASE PROMPTS
Each prompt is designed to be pasted into Claude Code (or triggered via /phase N). Do them in order.
Day plan
Day
Phases
Day 1
Phase 1 Scaffold · Phase 2 Database
Day 2
Phase 3 Auth & Tenancy · Phase 4 Slot engine & Booking
Day 3
Phase 5 Owner APIs & Stats · Phase 6 Public booking UI
Day 4
Phase 7 Owner dashboard UI · Phase 8 Notifications
Day 5
Phase 9 Hardening & E2E · Phase 10 Deploy & README


Phase 1 — Scaffold the monorepo
You are a senior full-stack engineer. Read CLAUDE.md and docs/GUIDE.md (Parts A3, A10).
 
Goal: scaffold the SlotEase monorepo exactly as in A10 — no business features yet.
 
Backend:
- FastAPI app factory in app/main.py with /health returning {"status":"ok"}.
- app/config.py using pydantic-settings: DATABASE_URL, JWT_SECRET, JWT_EXPIRE_MIN=60,
  CORS_ORIGINS, RESEND_API_KEY (optional), APP_BASE_URL.
- SQLAlchemy 2.0 engine/session in app/db.py; Alembic initialised and wired to settings.
- Global exception handlers producing {"error","message"}.
- ruff + mypy + pytest configured; one test for /health.
- Dockerfile (python:3.12-slim, uvicorn).
 
Frontend:
- Vite React TS + Tailwind + React Router + TanStack Query + Axios client reading VITE_API_URL.
- Placeholder routes: /:slug, /login, /register, /dashboard.
- Vitest + Testing Library configured with one smoke test.
 
Root: docker-compose.yml (postgres:16 with healthcheck, api), .env.example, .gitignore (.env, node_modules,
__pycache__, .venv), minimal README.
 
Acceptance: `docker compose up` works, GET /health → 200, `npm run dev` shows the placeholder,
/verify is green. Start in plan mode.
Phase 2 — Database schema & migrations
Read docs/GUIDE.md A5 carefully.
 
Implement SQLAlchemy models for all 6 tables with the ★ additions, and ONE Alembic migration that:
- enables extensions btree_gist and citext,
- creates all tables, FKs (ON DELETE CASCADE from businesses), CHECK constraints,
- creates the EXCLUDE constraint `no_overlapping_appointments` (WHERE status IN ('booked','completed')),
- creates the partial unique index on appointments (business_id, start_time) with the same WHERE,
- creates the indexes from A5.2.
Write the EXCLUDE constraint with op.execute() raw SQL — autogenerate will not produce it.
 
Add scripts/seed.py: business "Glow Salon" (slug glow-salon, Asia/Kolkata), owner
owner@glow.test / Passw0rd!, services Haircut 30m ₹300, Beard Trim 15m ₹150, Haircut + Beard 45m ₹420,
hours Tue–Sun 10:00–13:00 and 14:00–20:00, Monday closed; plus a second business "Care Physio".
 
Tests (tests/integration/test_constraints.py, against a real Postgres test DB):
- same start_time twice → IntegrityError
- 17:30–18:15 then 17:45–18:15 → IntegrityError (overlap)
- 17:00–17:30 then 17:30–18:00 → OK (back-to-back)
- cancelled 17:30 then new 17:30 → OK
- same slot in two different businesses → OK
 
Acceptance: `alembic upgrade head` on a clean DB, `alembic downgrade base` works, tests green.
Phase 3 — Auth & tenant isolation
Read docs/GUIDE.md A8 and A9 (auth rows).
 
Implement:
- core/security.py: bcrypt hash/verify (cost 12), create/decode JWT with claims sub, bid, role, exp.
- POST /auth/register: creates business + owner user in ONE transaction; validates slug regex and
  reserved words (login, register, dashboard, api, admin); 409 on duplicate slug/email.
- POST /auth/login: 401 with generic message on any failure.
- deps/tenant.py: get_current_tenant() → TenantContext(user_id, business_id, role); 401 on bad/expired token.
- repositories/ base pattern: every function requires business_id; write a helper `scoped(stmt, model, business_id)`.
- slowapi rate limit 5/min on /auth/*.
 
Use the test-writer subagent to write:
- register/login happy paths and failures,
- expired token → 401, tampered token → 401,
- tests/tenancy/conftest.py fixtures creating Business A and Business B with tokens (reused by later phases).
 
Frontend: Register and Login pages (React Hook Form + Zod), token stored in memory + localStorage,
Axios interceptor adds Bearer token and redirects to /login on 401, ProtectedRoute for /dashboard/*.
 
Acceptance: /verify green; then run /tenant-audit.
Phase 4 — Slot engine & booking API (the heart of the product)
Read docs/GUIDE.md A6 and A7 very carefully. This phase decides whether the product keeps its promise.
 
1. services/slots.py — pure function compute_free_slots() exactly as A6. No DB, inject `now`.
   Write unit tests FIRST covering every case in A12 "Unit — slots.py". Then implement.
2. Public endpoints:
   - GET /public/{slug}
   - GET /public/{slug}/services (active only)
   - GET /public/{slug}/slots?service_id&date → loads hours + busy intervals, calls compute_free_slots.
3. services/booking.py + POST /public/{slug}/bookings exactly as A7:
   - re-validate time against working hours and slot grid (422 OFF_GRID / OUTSIDE_HOURS),
   - upsert customer by (business_id, phone) with phone normalised to +91 E.164,
   - generate public_ref APT-YYYYMMDD-NNNN (per business per day, padded),
   - catch IntegrityError → 409 {"error":"SLOT_TAKEN","message":"This slot was just booked. Please pick another time."},
   - response body must match the sample in A9 byte-for-byte in shape and message format.
   - rate limit 10/min per IP.
4. Concurrency tests (tests/concurrency/):
   - 10 parallel bookings for the same slot with asyncio.gather → exactly one 201, nine 409.
   - 45-minute booking at 17:30 then 30-minute at 17:45 → 409.
   Use separate DB connections per request so the test is real.
 
Acceptance: all tests green, and `curl` twice on the same slot shows 201 then 409.
Start in plan mode and show me the test list before writing code.
Phase 5 — Owner APIs & stats
Read docs/GUIDE.md A9 (owner rows).
 
Implement, all through TenantContext and scoped repositories:
- GET /appointments?date= and ?from&to (joined customer name/phone, service name/price), ordered by start_time.
- PATCH /appointments/{id} with transition rules (booked → completed|cancelled|no_show; terminal = 422).
- Services CRUD (DELETE = is_active=false). Duration change doesn't alter existing appointments.
- GET/PUT /working-hours: PUT replaces the whole week in one transaction; validate no overlapping
  windows on the same weekday.
- GET /stats?month=YYYY-MM: total, completed, no_show, no_show_rate = no_show / (completed + no_show),
  revenue_estimate = sum(price of completed), busiest_weekday. Compute in SQL, not in Python loops.
- GET /dashboard/today summary: count, no-shows, estimated revenue (booked + completed).
 
Tenancy tests: with Business A's token try GET/PATCH/DELETE on every Business B resource → 404, and
assert list endpoints never contain B rows. Run /tenant-audit when done.
Phase 6 — Public booking page (mobile-first)
Read docs/GUIDE.md A11 (public booking). Use the frontend-design approach: clean, trustworthy, fast.
 
Build /:slug as a single page with 4 steps (service → date strip → slot chips → name/phone → confirm).
- Mobile-first at 360px; tap targets ≥ 48px; sticky Confirm button; no horizontal page scroll.
- TanStack Query for services/slots; skeleton loaders; empty and error states.
- Zod: name 2–60 chars, Indian mobile 10 digits (show +91 prefix).
- On 201: success screen with booking ref, formatted "Sat 10 Oct, 5:30 PM", wa.me link to the
  business with a prefilled message, "Book another".
- On 409: toast "This slot was just booked. Please pick another time.", invalidate slots query,
  keep name/phone filled.
- 404 slug: friendly "Business not found".
- Accessibility: labelled inputs, focus states, aria-live for errors.
 
Tests (Vitest + MSW): full happy path; 409 path refetches slots; validation messages.
Acceptance: Lighthouse mobile ≥ 90 for Performance and Accessibility.
Phase 7 — Owner dashboard
Read docs/GUIDE.md A11 (owner dashboard) and the "Output C" sample in the brief.
 
Build /dashboard with a sidebar (bottom nav on mobile): Today, Week, Services, Hours, Stats.
- Today: header "GLOW SALON | Today, Sat 10 Oct · 12 bookings · 2 no-shows · Est. ₹6,450";
  table TIME / CUSTOMER / SERVICE / STATUS; [Complete] [No-show] [Cancel] buttons only on 'booked' rows;
  optimistic updates with rollback on error; date picker to view other days.
- Week: 7-day grid, blocks positioned and sized by start/duration, colour by status.
- Services: table + modal form; deactivate toggle.
- Hours: per-weekday rows, "Closed" toggle, add break window; save calls PUT once.
- Stats: month selector; cards for bookings, no-show rate, revenue estimate, busiest day.
- Share card: copy public link + WhatsApp share.
Format currency with Intl.NumberFormat('en-IN', {style:'currency', currency:'INR'}).
 
Tests for status update flow and hours form validation.
Phase 8 — Notifications
Implement services/notify.py:
- Email via Resend when RESEND_API_KEY is set; otherwise log the message (dev mode). Never fail a booking
  because email failed — send in FastAPI BackgroundTasks, catch and log errors.
- Email to customer is optional (we only collect phone); email to the owner on every new booking.
- Build a WhatsApp click-to-chat URL: https://wa.me/<customer_phone>?text=<urlencoded confirmation>
  and expose it on dashboard rows so the owner can confirm with one tap.
- Confirmation text template: "Booking confirmed at {business}, {Sat 10 Oct, 5:30 PM}. Ref {APT-…}."
Tests: notify is called once per successful booking, never on 409; template formatting.
Phase 9 — Hardening & end-to-end test
1. Run the security-reviewer subagent over the whole backend; fix every Critical/High finding.
2. Add: CORS locked to CORS_ORIGINS, security headers middleware, request ID logging,
   structured JSON logs, pagination on list endpoints (limit ≤ 200).
3. Playwright E2E (frontend/e2e/booking.spec.ts) on a 390×844 viewport:
   register → add service → set hours → open public page → book → dashboard shows it → mark completed.
4. Playwright concurrency demo: two browser contexts click Confirm on the same slot → one success, one 409 toast.
5. Run /verify and report coverage for services/ and repositories/ (target ≥ 85%).
Phase 10 — Deploy & README
Prepare production deployment (I will run the dashboard steps myself; give me exact instructions):
- Neon: create DB, enable btree_gist and citext, run `alembic upgrade head` against it.
- Render: Docker web service from backend/, env vars from .env.example, health check /health,
  start command runs migrations then uvicorn.
- Vercel: frontend/ project, VITE_API_URL set, SPA rewrite so /:slug works on refresh (vercel.json).
- Update CORS_ORIGINS to the Vercel URL.
 
Write README.md with: what it does, live URLs, screenshot placeholders (booking page, dashboard, 409 demo),
local setup in ≤ 10 minutes, table of the 6 DB tables, API endpoint table, sample request/response
(201 and 409), how double booking is prevented (explain the EXCLUDE constraint), how tenancy is enforced,
test commands, and the Done Checklist with each item ticked and linked to its test.

Appendix 1 — Done Checklist Mapping
Brief checklist item
Where it is satisfied
Two browsers same slot → one 201, one 409
DB EXCLUDE + partial UNIQUE (Phase 2), 409 mapping (Phase 4), Playwright demo (Phase 9)
Business A can't touch Business B data
TenantContext + scoped repositories (Phase 3), tenancy tests (Phase 5), /tenant-audit
Slots respect hours, duration, bookings
compute_free_slots + unit tests (Phase 4)
Booking page works on mobile
Phase 6 + Lighthouse + Playwright mobile viewport
Hashed passwords, secrets in .env, live URL
Phase 3 (bcrypt), Phase 1 (settings), Phase 10 (deploy)
README: setup, tables, endpoints
Phase 10

Appendix 2 — Stretch Goals (after Day 5)
Stretch goal
Prompt seed for Claude Code
Razorpay advance payment
"Add a payments table and a pending_payment appointment status that holds the slot for 10 minutes. Create a Razorpay order on booking, verify the webhook signature, confirm on payment.captured, release the slot on expiry with a scheduled job. Include the pending status in the EXCLUDE constraint's WHERE clause."
WhatsApp reminder 2h before
"Add a reminders_sent_at column and a scheduled job every 10 minutes that finds booked appointments starting in 2h ± 10 min and sends a Twilio WhatsApp template message. Must be idempotent."
Multiple staff calendars
"Add a staff table and appointments.staff_id. Change the EXCLUDE constraint to staff_id WITH =. Slots are free if any qualified staff member is free; booking assigns the first free one inside the same transaction."

Appendix 3 — Prompting Tips for Claude Code
Point, don't paste: "Read docs/GUIDE.md A7" beats pasting the spec again — saves context.
Plan before code: use Plan Mode for every phase; reject plans that touch files outside the phase.
Tests are the contract: ask for the test list first, approve it, then implementation.
One concern per session: /clear between phases; CLAUDE.md keeps the memory.
Make it prove it: "Show me the failing test before the fix" catches hallucinated fixes.
Independent review: use the security-reviewer subagent — it didn't write the code, so it isn't grading itself.
Correct once, encode forever: add the rule to CLAUDE.md with #.
Never let it push: keep git push denied; you review the diff.
Appendix 4 — Submission (from the brief)
Push code to GitHub (clean structure, requirements.txt/package.json, .env.example).
Share the repo link in the WhatsApp group.
Record a short demo video showing: booking on mobile, the 409 on a second phone, dashboard status updates, stats, and the cross-tenant 404 test.
Final self-check: can someone run it in 10 minutes from your README, and does your output match the brief's Sample Output? If yes — submit.
GITHUB LINK: https://github.com/sundaji1969/Slotease_Appointment-booking-Saas

