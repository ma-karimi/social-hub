from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.models.platform_connection import PlatformConnectionModel
from social_hub.infrastructure.platforms.dto.incoming_event import IncomingEvent

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _load_connection(session, connection_id: UUID) -> PlatformConnection | None:
    """Load a Bale connection by ID without tenant scoping (webhook context)."""
    stmt = select(PlatformConnectionModel).where(
        PlatformConnectionModel.id == connection_id,
        PlatformConnectionModel.platform_type == PlatformType.BALE,
    )
    row = await session.scalar(stmt)
    if row is None:
        return None
    return PlatformConnection(
        id=row.id,
        tenant_id=row.tenant_id,
        platform_type=PlatformType(row.platform_type),
        credentials_encrypted=bytes(row.credentials_encrypted),
        settings=row.settings or {},
        is_active=row.is_active,
    )


@router.post("/{connection_id}", status_code=status.HTTP_200_OK)
async def bale_webhook(connection_id: UUID, request: Request):
    """
    Bale sends updates to this endpoint per-connection.
    Optionally verifies `X-Webhook-Secret` against connection settings.
    """
    container = request.app.state.container

    async with container.session_factory() as session:
        connection = await _load_connection(session, connection_id)

    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    if not connection.is_active:
        return {"ok": True}

    driver = container.driver_registry.get(PlatformType.BALE)

    body = await request.body()
    secret = connection.settings.get("webhook_secret")
    headers = dict(request.headers)
    # Allow secret via query string when Bale cannot send custom headers.
    query_secret = request.query_params.get("secret")
    if query_secret and "x-webhook-secret" not in {k.lower() for k in headers}:
        headers["x-webhook-secret"] = query_secret

    if not driver.verify_webhook(headers, body, secret):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    raw = await request.json()
    incoming: IncomingEvent | None = driver.parse_incoming(raw)

    if incoming is not None:
        credentials = container.encryptor.decrypt(connection.credentials_encrypted)
        await container.arq_redis.enqueue_job(
            "process_interaction_job",
            {
                "connection_id": str(connection.id),
                "tenant_id": str(connection.tenant_id),
                "platform_type": str(connection.platform_type),
                "credentials": credentials,
                "connection_settings": connection.settings,
                "incoming": {
                    "event_type": incoming.event_type,
                    "user_ref": incoming.user_ref,
                    "raw": incoming.raw,
                    "button_short_id": incoming.button_short_id,
                    "reply_chat_id": incoming.reply_chat_id,
                    "reply_message_id": incoming.reply_message_id,
                    "callback_query_id": incoming.callback_query_id,
                },
            },
        )

    return {"ok": True}
