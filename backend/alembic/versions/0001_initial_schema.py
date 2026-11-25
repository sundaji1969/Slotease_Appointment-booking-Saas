"""initial schema: 6 tables + double-booking constraints

Revision ID: 0001
Revises:
Create Date: 2026-11-25

Written by hand: autogenerate cannot produce the EXCLUDE constraint or partial indexes.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.execute(
        """
        CREATE TABLE businesses (
            id            UUID PRIMARY KEY,
            name          TEXT NOT NULL,
            slug          TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{3,40}$'),
            phone         TEXT,
            timezone      TEXT NOT NULL DEFAULT 'Asia/Kolkata',
            slot_step_min INT  NOT NULL DEFAULT 15 CHECK (slot_step_min BETWEEN 5 AND 120),
            plan          TEXT NOT NULL DEFAULT 'trial',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE users (
            id            UUID PRIMARY KEY,
            business_id   UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            email         CITEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'owner',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_users_role CHECK (role IN ('owner','staff'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE services (
            id           UUID PRIMARY KEY,
            business_id  UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            name         TEXT NOT NULL,
            duration_min INT  NOT NULL,
            price        NUMERIC(10,2) NOT NULL DEFAULT 0,
            is_active    BOOLEAN NOT NULL DEFAULT true,
            CONSTRAINT ck_services_duration CHECK (duration_min BETWEEN 5 AND 480),
            CONSTRAINT ck_services_price CHECK (price >= 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE working_hours (
            id          UUID PRIMARY KEY,
            business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            weekday     SMALLINT NOT NULL,
            open_time   TIME NOT NULL,
            close_time  TIME NOT NULL,
            CONSTRAINT ck_hours_weekday CHECK (weekday BETWEEN 0 AND 6),
            CONSTRAINT ck_hours_order CHECK (close_time > open_time)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE customers (
            id          UUID PRIMARY KEY,
            business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            phone       TEXT NOT NULL,
            CONSTRAINT uq_customers_business_phone UNIQUE (business_id, phone)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE appointments (
            id          UUID PRIMARY KEY,
            public_ref  TEXT NOT NULL,
            business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            service_id  UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            start_time  TIMESTAMPTZ NOT NULL,
            end_time    TIMESTAMPTZ NOT NULL,
            status      TEXT NOT NULL DEFAULT 'booked',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_appt_order CHECK (end_time > start_time),
            CONSTRAINT ck_appt_status CHECK (status IN ('booked','completed','cancelled','no_show')),
            CONSTRAINT uq_appt_business_ref UNIQUE (business_id, public_ref)
        )
        """
    )

    # THE double-booking guarantee: no two active appointments of one business may overlap in time.
    # '[)' = half-open, so back-to-back bookings (17:00-17:30, 17:30-18:00) are allowed.
    op.execute(
        """
        ALTER TABLE appointments
          ADD CONSTRAINT no_overlapping_appointments
          EXCLUDE USING gist (
            business_id WITH =,
            tstzrange(start_time, end_time, '[)') WITH &&
          ) WHERE (status IN ('booked','completed'))
        """
    )
    # The brief's UNIQUE (business_id, start_time), partial so cancelled slots can be re-booked.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_appt_business_start_active
          ON appointments (business_id, start_time)
          WHERE (status IN ('booked','completed'))
        """
    )

    # A5.2 indexes
    op.execute("CREATE INDEX ix_appt_business_start ON appointments (business_id, start_time)")
    op.execute("CREATE INDEX ix_services_business ON services (business_id) WHERE is_active")
    op.execute("CREATE INDEX ix_hours_business_weekday ON working_hours (business_id, weekday)")
    op.execute("CREATE INDEX ix_users_business ON users (business_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS appointments")
    op.execute("DROP TABLE IF EXISTS customers")
    op.execute("DROP TABLE IF EXISTS working_hours")
    op.execute("DROP TABLE IF EXISTS services")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS businesses")
