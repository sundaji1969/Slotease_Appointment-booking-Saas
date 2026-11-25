import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.deps.db import get_db
from app.deps.tenant import TenantContext, get_current_tenant
from app.repositories import services as service_repo
from app.schemas.owner import ServiceIn, ServiceOut, ServiceUpdate
from app.services import owner as owner_service

router = APIRouter(prefix="/services", tags=["owner: services"])


@router.get("", response_model=list[ServiceOut])
def list_services(
    tenant: TenantContext = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> list[ServiceOut]:
    return [ServiceOut.model_validate(s) for s in service_repo.list_services(db, tenant.business_id)]


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceIn, tenant: TenantContext = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> ServiceOut:
    return ServiceOut.model_validate(owner_service.create_service(db, tenant, data))


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(
    service_id: uuid.UUID, tenant: TenantContext = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> ServiceOut:
    return ServiceOut.model_validate(owner_service.get_service_or_404(db, tenant, service_id))


@router.put("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: uuid.UUID,
    data: ServiceUpdate,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> ServiceOut:
    return ServiceOut.model_validate(owner_service.update_service(db, tenant, service_id, data))


@router.delete("/{service_id}", response_model=ServiceOut)
def delete_service(
    service_id: uuid.UUID, tenant: TenantContext = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> ServiceOut:
    """Soft delete: the service is deactivated so past appointments keep their history."""
    return ServiceOut.model_validate(owner_service.deactivate_service(db, tenant, service_id))
