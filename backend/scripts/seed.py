"""Seed demo data: Glow Salon (owner@glow.test) and Care Physio (owner@carephysio.test), password Passw0rd!

Usage:  cd backend && python -m scripts.seed
Idempotent: existing demo businesses are deleted (cascade) and recreated.
"""

from datetime import time
from decimal import Decimal

from sqlalchemy import delete

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Business
from app.repositories import businesses, hours, services, users

DEMO_PASSWORD = "Passw0rd!"  # demo-only credential, documented in the README

SALON_HOURS = [(wd, time(10), time(13)) for wd in range(1, 7)] + [
    (wd, time(14), time(20)) for wd in range(1, 7)
]
PHYSIO_HOURS = [(wd, time(9), time(17)) for wd in range(0, 6)]


def seed() -> None:
    with SessionLocal() as db:
        db.execute(delete(Business).where(Business.slug.in_(["glow-salon", "care-physio"])))

        glow = businesses.create_business(db, "Glow Salon", "glow-salon", "+919876543210")
        users.create_user(db, glow.id, "owner@glow.test", hash_password(DEMO_PASSWORD))
        services.create_service(db, glow.id, "Haircut", 30, Decimal("300"))
        services.create_service(db, glow.id, "Beard Trim", 15, Decimal("150"))
        services.create_service(db, glow.id, "Haircut + Beard", 45, Decimal("420"))
        hours.replace_week(db, glow.id, SALON_HOURS)  # Monday (0) closed

        physio = businesses.create_business(db, "Care Physio", "care-physio", "+919812345678")
        users.create_user(db, physio.id, "owner@carephysio.test", hash_password(DEMO_PASSWORD))
        services.create_service(db, physio.id, "Initial Assessment", 60, Decimal("800"))
        services.create_service(db, physio.id, "Follow-up Session", 30, Decimal("500"))
        hours.replace_week(db, physio.id, PHYSIO_HOURS)

        db.commit()
    print("Seeded: glow-salon (owner@glow.test) and care-physio (owner@carephysio.test), password Passw0rd!")


if __name__ == "__main__":
    seed()
