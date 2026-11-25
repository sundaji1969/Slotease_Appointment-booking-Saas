from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.deps.db import get_db
from app.deps.tenant import TenantContext, get_current_tenant
from app.repositories import hours as hours_repo
from app.schemas.owner import HourIn, HourOut
from app.services import owner as owner_service

router = APIRouter(prefix="/working-hours", tags=["owner: working hours"])


@router.get("", response_model=list[HourOut])
def get_hours(
    tenant: TenantContext = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> list[HourOut]:
    return [HourOut.model_validate(h) for h in hours_repo.list_hours(db, tenant.business_id)]


@router.put("", response_model=list[HourOut])
def replace_hours(
    rows: list[HourIn] = Body(max_length=50),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> list[HourOut]:
    owner_service.replace_hours(db, tenant, rows)
    return [HourOut.model_validate(h) for h in hours_repo.list_hours(db, tenant.business_id)]
