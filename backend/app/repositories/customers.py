import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Customer


def upsert_customer(db: Session, business_id: uuid.UUID, name: str, phone: str) -> uuid.UUID:
    """One customer row per (business, phone); the latest name wins. Returns the customer id."""
    stmt = (
        insert(Customer)
        .values(id=uuid.uuid4(), business_id=business_id, name=name, phone=phone)
        .on_conflict_do_update(constraint="uq_customers_business_phone", set_={"name": name})
        .returning(Customer.id)
    )
    return db.execute(stmt).scalar_one()
