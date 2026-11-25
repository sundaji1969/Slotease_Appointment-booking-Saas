"""Owner-side business logic: appointments, services, working hours. Always scoped by TenantContext."""

import uuid
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.errors import NotFound, Unprocessable
from app.core.formatting import confirmation_text, whatsapp_url
from app.deps.tenant import TenantContext
from app.models import Business, Service
from app.repositories import appointments as appt_repo
from app.repositories import businesses as business_repo
from app.repositories import hours as hours_repo
from app.repositories import services as service_repo
from app.schemas.owner import AppointmentOut, HourIn, ServiceIn, ServiceUpdate, TodayOut
from app.services.timeutil import day_bounds

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "booked": {"completed", "cancelled", "no_show"},
    "completed": set(),
    "cancelled": set(),
    "no_show": set(),
}


def current_business(db: Session, tenant: TenantContext) -> Business:
    biz = business_repo.get_business(db, tenant.business_id)
    if biz is None:  # token for a deleted business
        raise NotFound("Business not found", code="BUSINESS_NOT_FOUND")
    return biz


def _to_out(row: Any, biz: Business, tz: ZoneInfo) -> AppointmentOut:
    start_local = row.start_time.astimezone(tz)
    return AppointmentOut(
        id=row.id,
        booking_id=row.public_ref,
        start_time=start_local,
        end_time=row.end_time.astimezone(tz),
        status=row.status,
        customer_name=row.customer_name,
        customer_phone=row.customer_phone,
        service_id=row.service_id,
        service_name=row.service_name,
        price=float(row.price),
        whatsapp_url=whatsapp_url(
            row.customer_phone, confirmation_text(biz.name, start_local, row.public_ref)
        ),
    )


# ---------- appointments ----------


def list_appointments(
    db: Session,
    tenant: TenantContext,
    day: date | None,
    from_day: date | None,
    to_day: date | None,
    limit: int,
    offset: int,
    now: datetime,
) -> list[AppointmentOut]:
    biz = current_business(db, tenant)
    tz = ZoneInfo(biz.timezone)
    if day is not None:
        start, end = day_bounds(day, tz)
    elif from_day is not None and to_day is not None:
        if to_day < from_day:
            raise Unprocessable("INVALID_RANGE", "'to' must be on or after 'from'")
        if (to_day - from_day).days > 62:
            raise Unprocessable("INVALID_RANGE", "Range may cover at most 62 days")
        start, _ = day_bounds(from_day, tz)
        _, end = day_bounds(to_day, tz)
    else:
        start, end = day_bounds(now.astimezone(tz).date(), tz)
    rows = appt_repo.list_appointments(db, tenant.business_id, start, end, limit=limit, offset=offset)
    return [_to_out(r, biz, tz) for r in rows]


def update_status(
    db: Session, tenant: TenantContext, appointment_id: uuid.UUID, new_status: str
) -> AppointmentOut:
    biz = current_business(db, tenant)
    appt = appt_repo.get_appointment(db, tenant.business_id, appointment_id)
    if appt is None:
        raise NotFound("Appointment not found")
    if new_status not in ALLOWED_TRANSITIONS[appt.status]:
        raise Unprocessable(
            "INVALID_TRANSITION", f"Cannot change an appointment from {appt.status} to {new_status}"
        )
    appt.status = new_status
    db.commit()
    row = appt_repo.get_appointment_row(db, tenant.business_id, appointment_id)
    assert row is not None
    return _to_out(row, biz, ZoneInfo(biz.timezone))


def today_summary(db: Session, tenant: TenantContext, day: date | None, now: datetime) -> TodayOut:
    biz = current_business(db, tenant)
    tz = ZoneInfo(biz.timezone)
    day = day or now.astimezone(tz).date()
    start, end = day_bounds(day, tz)
    s = appt_repo.day_summary(db, tenant.business_id, start, end)
    return TodayOut(
        date=day,
        business_name=biz.name,
        count=s.count,
        no_shows=s.no_shows,
        revenue_estimate=float(s.revenue_estimate),
    )


# ---------- services ----------


def get_service_or_404(db: Session, tenant: TenantContext, service_id: uuid.UUID) -> Service:
    svc = service_repo.get_service(db, tenant.business_id, service_id)
    if svc is None:
        raise NotFound("Service not found", code="SERVICE_NOT_FOUND")
    return svc


def create_service(db: Session, tenant: TenantContext, data: ServiceIn) -> Service:
    svc = service_repo.create_service(db, tenant.business_id, data.name, data.duration_min, data.price)
    db.commit()
    return svc


def update_service(db: Session, tenant: TenantContext, service_id: uuid.UUID, data: ServiceUpdate) -> Service:
    """Duration changes affect only future bookings; existing appointments keep their stored end_time."""
    svc = get_service_or_404(db, tenant, service_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(svc, field, value)
    db.commit()
    return svc


def deactivate_service(db: Session, tenant: TenantContext, service_id: uuid.UUID) -> Service:
    svc = get_service_or_404(db, tenant, service_id)
    svc.is_active = False
    db.commit()
    return svc


# ---------- working hours ----------


def replace_hours(db: Session, tenant: TenantContext, rows: list[HourIn]) -> None:
    by_day: dict[int, list[HourIn]] = {}
    for r in rows:
        by_day.setdefault(r.weekday, []).append(r)
    for wd, windows in by_day.items():
        windows.sort(key=lambda w: w.open_time)
        for a, b in zip(windows, windows[1:], strict=False):
            if b.open_time < a.close_time:
                raise Unprocessable("OVERLAPPING_HOURS", f"Working windows overlap on weekday {wd}")
    hours_repo.replace_week(db, tenant.business_id, [(r.weekday, r.open_time, r.close_time) for r in rows])
    db.commit()
