from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from social_hub.api.deps import TenantContextDep, get_connection_service
from social_hub.api.schemas.connections import (
    ConnectionResponse,
    CreateConnectionRequest,
    UpdateConnectionRequest,
)
from social_hub.application.services.connection_service import ConnectionService
from social_hub.domain.exceptions import ConnectionNotFoundError
from social_hub.domain.value_objects.platform_type import PlatformType

router = APIRouter()


def _to_response(conn) -> ConnectionResponse:
    return ConnectionResponse(
        id=str(conn.id),
        tenant_id=str(conn.tenant_id),
        platform_type=conn.platform_type,
        settings=conn.settings,
        is_active=conn.is_active,
    )


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: CreateConnectionRequest,
    tenant_ctx: TenantContextDep,
    connection_service: Annotated[ConnectionService, Depends(get_connection_service)],
):
    try:
        platform = PlatformType(body.platform_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {body.platform_type}")

    conn = await connection_service.create_connection(
        tenant_ctx=tenant_ctx,
        platform_type=platform,
        credentials=body.credentials,
        settings=body.settings,
    )
    return _to_response(conn)


@router.get("", response_model=list[ConnectionResponse])
async def list_connections(
    tenant_ctx: TenantContextDep,
    connection_service: Annotated[ConnectionService, Depends(get_connection_service)],
):
    conns = await connection_service.list_connections(tenant_ctx)
    return [_to_response(c) for c in conns]


@router.patch("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: UUID,
    body: UpdateConnectionRequest,
    tenant_ctx: TenantContextDep,
    connection_service: Annotated[ConnectionService, Depends(get_connection_service)],
):
    try:
        conn = await connection_service.update_connection(
            tenant_ctx=tenant_ctx,
            connection_id=connection_id,
            credentials=body.credentials,
            settings=body.settings,
            is_active=body.is_active,
        )
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _to_response(conn)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: UUID,
    tenant_ctx: TenantContextDep,
    connection_service: Annotated[ConnectionService, Depends(get_connection_service)],
):
    try:
        await connection_service.delete_connection(tenant_ctx, connection_id)
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")


@router.post("/{connection_id}/test")
async def test_connection(
    connection_id: UUID,
    tenant_ctx: TenantContextDep,
    connection_service: Annotated[ConnectionService, Depends(get_connection_service)],
):
    try:
        conn = await connection_service.get_connection(tenant_ctx, connection_id)
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        credentials = connection_service.decrypt_credentials(conn)
        bot_token = credentials.get("bot_token")
        if not bot_token:
            return {"ok": False, "error": "credentials.bot_token is required"}

        if conn.platform_type == PlatformType.TELEGRAM:
            from social_hub.infrastructure.platforms.telegram.client import TelegramClient

            me = await TelegramClient(bot_token).get_me()
            return {"ok": True, "bot": me}

        if conn.platform_type == PlatformType.BALE:
            from social_hub.infrastructure.platforms.bale.client import BaleClient

            me = await BaleClient(bot_token).get_me()
            return {"ok": True, "bot": me}

        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
