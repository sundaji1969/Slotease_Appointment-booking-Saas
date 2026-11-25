import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Row, func, select, text
from sqlalchemy.orm import Session

from app.models import Appointment, Customer, Service
from app.repositories.base import scoped

ACTIVE_STATUSES = ("booked", "completed")


def busy_intervals(
    db: Session, business_id: uuid.UUID, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    """Active appointments overlapping [start, end)."""
    stmt = scoped(select(Appointment.start_time, Appointment.end_time), Appointment, business_id).where(
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.start_time < end,
        Appointment.end_time > start,
    )
    return [(r.start_time, r.end_time) for r in db.execute(stmt)]


def lock_business_day(db: Session, business_id: uuid.UUID, day: date) -> None:
    """Transaction-scoped advisory lock so public_ref numbering per business/day can't collide.
    This is NOT the double-booking protection (the EXCLUDE constraint is)."""
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
        {"k": f"{business_id}:{day.isoformat()}"},
    )


def next_public_ref(db: Session, business_id: uuid.UUID, day: date) -> str:
    prefix = f"APT-{day:%Y%m%d}-"
    stmt = scoped(select(func.count()).select_from(Appointment), Appointment, business_id).where(
        Appointment.public_ref.like(prefix + "%")
    )
    n = (db.scalar(stmt) or 0) + 1
    return f"{prefix}{n:04d}"


def insert_appointment(
    db: Session,
    business_id: uuid.UUID,
    service_id: uuid.UUID,
    customer_id: uuid.UUID,
    start: datetime,
    end: datetime,
    public_ref: str,
) -> Appointment:
    appt = Appointment(
        id=uuid.uuid4(),
        public_ref=public_ref,
        business_id=business_id,
        service_id=service_id,
        customer_id=customer_id,
        start_time=start,
        end_time=end,
        status="booked",
    )
    db.add(appt)
    db.flush()  # constraint violations surface here as IntegrityError
    return appt


_LIST_COLUMNS = (
    Appointment.id,
    Appointment.public_ref,
    Appointment.start_time,
    Appointment.end_time,
    Appointment.status,
    Customer.name.label("customer_name"),
    Customer.phone.label("customer_phone"),
    Service.id.label("service_id"),
    Service.name.label("service_name"),
    Service.price.label("price"),
)


def _joined(business_id: uuid.UUID):  # type: ignore[no-untyped-def]
    # Joins are also constrained to the same tenant: defence in depth.
    return (
        scoped(select(*_LIST_COLUMNS), Appointment, business_id)
        .join(Customer, (Customer.id == Appointment.customer_id) & (Customer.business_id == business_id))
        .join(Service, (Service.id == Appointment.service_id) & (Service.business_id == business_id))
    )


def list_appointments(
    db: Session, business_id: uuid.UUID, start: datetime, end: datetime, limit: int = 200, offset: int = 0
) -> list[Row]:  # type: ignore[type-arg]
    stmt = (
        _joined(business_id)
        .where(Appointment.start_time >= start, Appointment.start_time < end)
        .order_by(Appointment.start_time)
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt))


def get_appointment_row(db: Session, business_id: uuid.UUID, appointment_id: uuid.UUID) -> Row | None:  # type: ignore[type-arg]
    return db.execute(_joined(business_id).where(Appointment.id == appointment_id)).first()


def get_appointment(db: Session, business_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment | None:
    stmt = scoped(select(Appointment), Appointment, business_id).where(Appointment.id == appointment_id)
    return db.scalar(stmt.with_for_update())


@dataclass(frozen=True)
class DaySummary:
    count: int
    no_shows: int
    revenue_estimate: Decimal


def day_summary(db: Session, business_id: uuid.UUID, start: datetime, end: datetime) -> DaySummary:
    stmt = (
        scoped(
            select(
                func.count().filter(Appointment.status != "cancelled"),
                func.count().filter(Appointment.status == "no_show"),
                func.coalesce(func.sum(Service.price).filter(Appointment.status.in_(ACTIVE_STATUSES)), 0),
            ),
            Appointment,
            business_id,
        )
        .join(Service, (Service.id == Appointment.service_id) & (Service.business_id == business_id))
        .where(Appointment.start_time >= start, Appointment.start_time < end)
    )
    count, no_shows, revenue = db.execute(stmt).one()
    return DaySummary(count=count, no_shows=no_shows, revenue_estimate=Decimal(revenue))


@dataclass(frozen=True)
class MonthStats:
    total: int
    completed: int
    no_show: int
    cancelled: int
    revenue_estimate: Decimal
    busiest_weekday: int | None  # ISO: 1 = Monday … 7 = Sunday


def month_stats(db: Session, business_id: uuid.UUID, start: datetime, end: datetime, tz: str) -> MonthStats:
    totals = (
        scoped(
            select(
                func.count().filter(Appointment.status != "cancelled"),
                func.count().filter(Appointment.status == "completed"),
                func.count().filter(Appointment.status == "no_show"),
                func.count().filter(Appointment.status == "cancelled"),
                func.coalesce(func.sum(Service.price).filter(Appointment.status == "completed"), 0),
            ),
            Appointment,
            business_id,
        )
        .join(Service, (Service.id == Appointment.service_id) & (Service.business_id == business_id))
        .where(Appointment.start_time >= start, Appointment.start_time < end)
    )
    total, completed, no_show, cancelled, revenue = db.execute(totals).one()

    isodow = func.extract("isodow", func.timezone(tz, Appointment.start_time))
    busiest = (
        scoped(select(isodow.label("dow"), func.count().label("n")), Appointment, business_id)
        .where(
            Appointment.start_time >= start,
            Appointment.start_time < end,
            Appointment.status != "cancelled",
        )
        .group_by("dow")
        .order_by(func.count().desc(), "dow")
        .limit(1)
    )
    row = db.execute(busiest).first()
    return MonthStats(
        total=total,
        completed=completed,
        no_show=no_show,
        cancelled=cancelled,
        revenue_estimate=Decimal(revenue),
        busiest_weekday=int(row.dow) if row else None,
    )
