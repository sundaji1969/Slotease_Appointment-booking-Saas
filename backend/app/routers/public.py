import uuid
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.core.ratelimit import ASSISTANT_LIMIT, BOOKING_LIMIT, limiter
from app.deps.clock import get_now
from app.deps.db import get_db
from app.repositories import services as service_repo
from app.schemas.public import (
    AssistantIn,
    AssistantOut,
    BookingIn,
    BookingOut,
    PublicBusinessOut,
    PublicServiceOut,
    SlotsOut,
)
from app.services import assistant as assistant_service
from app.services import booking as booking_service
from app.services import notify

router = APIRouter(prefix="/public", tags=["public"])

Slug = Path(pattern=r"^[a-z0-9-]{3,40}$")


@router.get("/{slug}", response_model=PublicBusinessOut)
def get_business(slug: str = Slug, db: Session = Depends(get_db)) -> PublicBusinessOut:
    biz = booking_service.get_business_or_404(db, slug)
    return PublicBusinessOut(
        name=biz.name,
        slug=biz.slug,
        phone=biz.phone,
        timezone=biz.timezone,
        assistant_enabled=assistant_service.is_enabled(),
    )


@router.get("/{slug}/services", response_model=list[PublicServiceOut])
def list_services(slug: str = Slug, db: Session = Depends(get_db)) -> list[PublicServiceOut]:
    biz = booking_service.get_business_or_404(db, slug)
    return [
        PublicServiceOut(id=s.id, name=s.name, duration_min=s.duration_min, price=float(s.price))
        for s in service_repo.list_services(db, biz.id, active_only=True)
    ]


@router.get("/{slug}/slots", response_model=SlotsOut)
def list_slots(
    service_id: uuid.UUID,
    date: date = Query(),
    slug: str = Slug,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> SlotsOut:
    return SlotsOut(date=date, slots=booking_service.list_free_slots(db, slug, service_id, date, now))


@router.post("/{slug}/bookings", status_code=status.HTTP_201_CREATED, response_model=BookingOut)
@limiter.limit(BOOKING_LIMIT)
def create_booking(
    request: Request,
    data: BookingIn,
    background: BackgroundTasks,
    slug: str = Slug,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> BookingOut:
    out, notice = booking_service.create_booking(db, slug, data, now)
    background.add_task(notify.notify_new_booking, notice)
    return out


@router.post("/{slug}/assistant", response_model=AssistantOut)
@limiter.limit(ASSISTANT_LIMIT)
def ask_assistant(
    request: Request,
    data: AssistantIn,
    slug: str = Slug,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> AssistantOut:
    """Natural-language slot finder. Suggests real free slots; booking still goes through /bookings."""
    return assistant_service.suggest(db, slug, data, now)
