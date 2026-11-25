"""Public booking flow (GUIDE A7). The database decides who wins a slot; we translate its verdict."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import SLOT_TAKEN_MESSAGE, Conflict, NotFound, Unprocessable
from app.core.formatting import confirmation_text, human_datetime
from app.models import Business, Service
from app.repositories import appointments as appt_repo
from app.repositories import businesses as business_repo
from app.repositories import customers as customer_repo
from app.repositories import hours as hours_repo
from app.repositories import services as service_repo
from app.schemas.public import BookingIn, BookingOut
from app.services import slots
from app.services.timeutil import day_bounds

SLOT_CONSTRAINTS = ("no_overlapping_appointments", "uq_appt_business_start_active")


def get_business_or_404(db: Session, slug: str) -> Business:
    biz = business_repo.get_by_slug(db, slug)
    if biz is None:
        raise NotFound("Business not found", code="BUSINESS_NOT_FOUND")
    return biz


def get_active_service_or_404(db: Session, business_id: uuid.UUID, service_id: uuid.UUID) -> Service:
    svc = service_repo.get_service(db, business_id, service_id)
    if svc is None or not svc.is_active:
        raise NotFound("Service not found", code="SERVICE_NOT_FOUND")
    return svc


def list_free_slots(
    db: Session, slug: str, service_id: uuid.UUID, day: date, now: datetime
) -> list[datetime]:
    biz = get_business_or_404(db, slug)
    svc = get_active_service_or_404(db, biz.id, service_id)
    tz = ZoneInfo(biz.timezone)
    windows = hours_repo.windows_for_weekday(db, biz.id, day.weekday())
    start, end = day_bounds(day, tz)
    busy = appt_repo.busy_intervals(db, biz.id, start, end)
    try:
        return slots.compute_free_slots(
            day=day,
            tz=tz,
            working_windows=windows,
            busy=busy,
            duration_min=svc.duration_min,
            step_min=biz.slot_step_min,
            now=now,
            lead_time_min=settings.LEAD_TIME_MIN,
            max_days_ahead=settings.MAX_DAYS_AHEAD,
        )
    except slots.SlotError as exc:
        raise Unprocessable(exc.code, exc.message) from exc


@dataclass(frozen=True)
class BookingNotice:
    """Plain data handed to the background notifier (no ORM objects, no session)."""

    business_id: uuid.UUID
    business_name: str
    public_ref: str
    service_name: str
    customer_name: str
    customer_phone: str
    start_local: datetime


def _is_slot_conflict(exc: IntegrityError) -> bool:
    diag = getattr(exc.orig, "diag", None)
    name = getattr(diag, "constraint_name", None) or ""
    return name in SLOT_CONSTRAINTS or any(c in str(exc.orig) for c in SLOT_CONSTRAINTS)


def create_booking(
    db: Session, slug: str, data: BookingIn, now: datetime
) -> tuple[BookingOut, BookingNotice]:
    biz = get_business_or_404(db, slug)
    svc = get_active_service_or_404(db, biz.id, data.service_id)
    tz = ZoneInfo(biz.timezone)

    start = data.start_time if data.start_time.tzinfo else data.start_time.replace(tzinfo=tz)
    start_local = start.astimezone(tz)
    windows = hours_repo.windows_for_weekday(db, biz.id, start_local.weekday())
    try:
        slots.check_bookable_start(
            start_local,
            tz,
            windows,
            svc.duration_min,
            biz.slot_step_min,
            now,
            lead_time_min=settings.LEAD_TIME_MIN,
            max_days_ahead=settings.MAX_DAYS_AHEAD,
        )
    except slots.SlotError as exc:
        raise Unprocessable(exc.code, exc.message) from exc

    end_local = start_local + timedelta(minutes=svc.duration_min)
    try:
        customer_id = customer_repo.upsert_customer(db, biz.id, data.name, data.phone)
        appt_repo.lock_business_day(db, biz.id, start_local.date())
        ref = appt_repo.next_public_ref(db, biz.id, start_local.date())
        appt_repo.insert_appointment(db, biz.id, svc.id, customer_id, start_local, end_local, ref)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_slot_conflict(exc):
            raise Conflict("SLOT_TAKEN", SLOT_TAKEN_MESSAGE) from exc
        raise

    out = BookingOut(
        booking_id=ref,
        service=svc.name,
        start_time=start_local,
        end_time=end_local,
        status="booked",
        message=f"Booking confirmed at {biz.name}, {human_datetime(start_local)}",
    )
    notice = BookingNotice(
        business_id=biz.id,
        business_name=biz.name,
        public_ref=ref,
        service_name=svc.name,
        customer_name=data.name,
        customer_phone=data.phone,
        start_local=start_local,
    )
    return out, notice


__all__ = ["BookingNotice", "confirmation_text", "create_booking", "list_free_slots"]
