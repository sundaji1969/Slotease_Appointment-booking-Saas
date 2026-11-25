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
