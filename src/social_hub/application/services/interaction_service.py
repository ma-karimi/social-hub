from datetime import datetime, timezone

import httpx
import structlog

from social_hub.domain.entities.interaction_event import InteractionEvent, InteractionStatus, ReplyContext
from social_hub.domain.repositories.button_repo import ButtonRepository
from social_hub.domain.repositories.interaction_event_repo import InteractionEventRepository
from social_hub.domain.repositories.tenant_repo import TenantRepository
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.dto.incoming_event import IncomingEvent
from social_hub.infrastructure.platforms.registry import DriverRegistry

logger = structlog.get_logger(__name__)


class InteractionService:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        button_repo: ButtonRepository,
        interaction_event_repo: InteractionEventRepository,
        driver_registry: DriverRegistry,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._button_repo = button_repo
        self._event_repo = interaction_event_repo
        self._driver_registry = driver_registry

    async def handle(
        self,
        incoming: IncomingEvent,
        connection_ctx: ConnectionContext,
    ) -> None:
        """
        Resolve button from short_id, persist InteractionEvent,
        and notify the Panel webhook if configured.
        """
        tenant_id = connection_ctx.connection.tenant_id
        platform_type = connection_ctx.connection.platform_type

        button = None
        action = None
        payload: dict = {}

        if incoming.button_short_id:
            button = await self._button_repo.get_by_short_id(incoming.button_short_id)
            if button:
                action = button.action_type
                payload = button.payload

        reply_context = None
        if incoming.reply_chat_id:
            reply_context = ReplyContext(
                chat_id=incoming.reply_chat_id,
                message_id=incoming.reply_message_id,
                callback_query_id=incoming.callback_query_id,
            )

        event = InteractionEvent.create(
            tenant_id=tenant_id,
            platform_type=platform_type,
            user_platform_id=incoming.user_ref,
            raw_payload=incoming.raw,
            button_id=button.id if button else None,
            action=action,
            payload=payload,
            reply_context=reply_context,
        )
        event = await self._event_repo.create(event)

        tenant = await self._tenant_repo.get_by_id(tenant_id)

        # Acknowledge callback to remove Telegram spinner
        if incoming.callback_query_id:
            try:
                driver = self._driver_registry.get(PlatformType(platform_type))
                await driver.reply_to_interaction(
                    ctx=connection_ctx,
                    chat_id=incoming.reply_chat_id or "",
                    text="",
                    callback_query_id=incoming.callback_query_id,
                )
            except Exception:
                logger.warning("callback_ack_failed", event_id=str(event.id))

        if tenant and tenant.webhook_callback_url:
            await self._notify_panel(tenant.webhook_callback_url, event)

        event.status = InteractionStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        await self._event_repo.update(event)

    async def _notify_panel(self, webhook_url: str, event: InteractionEvent) -> None:
        payload = {
            "event_id": str(event.id),
            "tenant_id": str(event.tenant_id),
            "platform_type": event.platform_type,
            "action": event.action,
            "payload": event.payload,
            "user_platform_id": event.user_platform_id,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(webhook_url, json=payload)
        except Exception as exc:
            logger.warning("panel_webhook_failed", url=webhook_url, error=str(exc))
