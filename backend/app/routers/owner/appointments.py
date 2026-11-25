import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps.clock import get_now
from app.deps.db import get_db
from app.deps.tenant import TenantContext, get_current_tenant
from app.schemas.owner import AppointmentOut, StatusPatch, TodayOut
from app.services import owner as owner_service

router = APIRouter(tags=["owner: appointments"])


@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(
    date: date | None = Query(default=None),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[AppointmentOut]:
    return owner_service.list_appointments(db, tenant, date, from_, to, limit, offset, now)


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: uuid.UUID,
    data: StatusPatch,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> AppointmentOut:
    return owner_service.update_status(db, tenant, appointment_id, data.status)


@router.get("/dashboard/today", response_model=TodayOut)
def today(
    date: date | None = Query(default=None),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> TodayOut:
    return owner_service.today_summary(db, tenant, date, now)
