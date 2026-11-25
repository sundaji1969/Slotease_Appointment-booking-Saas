import uuid
from datetime import time

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import WorkingHour
from app.repositories.base import scoped


def list_hours(db: Session, business_id: uuid.UUID) -> list[WorkingHour]:
    stmt = scoped(select(WorkingHour), WorkingHour, business_id).order_by(
        WorkingHour.weekday, WorkingHour.open_time
    )
    return list(db.scalars(stmt))


def windows_for_weekday(db: Session, business_id: uuid.UUID, weekday: int) -> list[tuple[time, time]]:
    stmt = (
        scoped(select(WorkingHour.open_time, WorkingHour.close_time), WorkingHour, business_id)
        .where(WorkingHour.weekday == weekday)
        .order_by(WorkingHour.open_time)
    )
    return [(row.open_time, row.close_time) for row in db.execute(stmt)]


def replace_week(db: Session, business_id: uuid.UUID, rows: list[tuple[int, time, time]]) -> None:
    """Delete-and-insert inside the caller's transaction (caller commits)."""
    db.execute(delete(WorkingHour).where(WorkingHour.business_id == business_id))
    db.add_all(
        WorkingHour(id=uuid.uuid4(), business_id=business_id, weekday=wd, open_time=o, close_time=c)
        for wd, o, c in rows
    )
    db.flush()
