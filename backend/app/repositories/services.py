import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Service
from app.repositories.base import scoped


def list_services(db: Session, business_id: uuid.UUID, active_only: bool = False) -> list[Service]:
    stmt = scoped(select(Service), Service, business_id)
    if active_only:
        stmt = stmt.where(Service.is_active.is_(True))
    return list(db.scalars(stmt.order_by(Service.name)))


def get_service(db: Session, business_id: uuid.UUID, service_id: uuid.UUID) -> Service | None:
    stmt = scoped(select(Service), Service, business_id).where(Service.id == service_id)
    return db.scalar(stmt)


def create_service(
    db: Session, business_id: uuid.UUID, name: str, duration_min: int, price: Decimal
) -> Service:
    svc = Service(
        id=uuid.uuid4(),
        business_id=business_id,
        name=name,
        duration_min=duration_min,
        price=price,
        is_active=True,
    )
    db.add(svc)
    db.flush()
    return svc
