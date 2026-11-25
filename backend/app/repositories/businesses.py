"""Tenant resolution. `get_by_slug` is the only lookup that does not take business_id —
it is how a public request discovers which tenant it belongs to."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Business


def get_by_slug(db: Session, slug: str) -> Business | None:
    return db.scalar(select(Business).where(Business.slug == slug))


def get_business(db: Session, business_id: uuid.UUID) -> Business | None:
    return db.get(Business, business_id)


def slug_exists(db: Session, slug: str) -> bool:
    return db.scalar(select(Business.id).where(Business.slug == slug)) is not None


def create_business(db: Session, name: str, slug: str, phone: str | None) -> Business:
    biz = Business(id=uuid.uuid4(), name=name, slug=slug, phone=phone)
    db.add(biz)
    db.flush()
    return biz
