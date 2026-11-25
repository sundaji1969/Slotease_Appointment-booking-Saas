from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps.db import get_db
from app.deps.tenant import TenantContext, get_current_tenant
from app.schemas.auth import BusinessOut
from app.schemas.owner import StatsOut
from app.services import owner as owner_service
from app.services import stats as stats_service

router = APIRouter(tags=["owner: stats"])


@router.get("/stats", response_model=StatsOut)
def get_stats(
    month: str = Query(pattern=r"^\d{4}-\d{2}$"),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> StatsOut:
    return stats_service.month_stats(db, tenant, month)


@router.get("/me", response_model=BusinessOut)
def me(tenant: TenantContext = Depends(get_current_tenant), db: Session = Depends(get_db)) -> BusinessOut:
    """The logged-in owner's business (name, slug for the share link, timezone)."""
    return BusinessOut.model_validate(owner_service.current_business(db, tenant))
