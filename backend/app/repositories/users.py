"""Users. `get_by_email` is global by nature (login happens before we know the tenant)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def email_exists(db: Session, email: str) -> bool:
    return db.scalar(select(User.id).where(User.email == email)) is not None


def create_user(
    db: Session, business_id: uuid.UUID, email: str, password_hash: str, role: str = "owner"
) -> User:
    user = User(id=uuid.uuid4(), business_id=business_id, email=email, password_hash=password_hash, role=role)
    db.add(user)
    db.flush()
    return user


def owner_emails(db: Session, business_id: uuid.UUID) -> list[str]:
    rows = db.scalars(select(User.email).where(User.business_id == business_id, User.role == "owner"))
    return list(rows)
