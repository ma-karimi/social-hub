from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from social_hub.api.deps import get_tenant_service
from social_hub.api.schemas.tenants import (
    CreateTenantRequest,
    CreateTenantResponse,
    TenantResponse,
)
from social_hub.application.services.tenant_service import TenantService
from social_hub.domain.exceptions import TenantNotFoundError

router = APIRouter()


@router.post("", response_model=CreateTenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: CreateTenantRequest,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
):
    tenant, api_key = await tenant_service.create_tenant(
        name=body.name, settings=body.settings
    )
    return CreateTenantResponse(
        tenant=TenantResponse(
            id=str(tenant.id),
            name=tenant.name,
            is_active=tenant.is_active,
            settings=tenant.settings,
        ),
        api_key=api_key,
    )


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
):
    tenants = await tenant_service.list_tenants()
    return [
        TenantResponse(id=str(t.id), name=t.name, is_active=t.is_active, settings=t.settings)
        for t in tenants
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
):
    try:
        tenant = await tenant_service.get_tenant(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        is_active=tenant.is_active,
        settings=tenant.settings,
    )


@router.post("/{tenant_id}/regenerate-key", response_model=dict)
async def regenerate_api_key(
    tenant_id: UUID,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
):
    try:
        _, api_key = await tenant_service.regenerate_api_key(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"api_key": api_key}
