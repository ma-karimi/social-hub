"""Unified social webhooks for Instagram provider + Telegram/Bale."""

from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, Header, Request

from social_hub.config import get_settings
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.repositories.social_account_repo import (
    SQLAlchemySocialAccountRepo,
)
from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo
from social_hub.infrastructure.providers.zernio.mappers import normalize_webhook_event

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["social-webhooks"])


@router.post("/webhooks/social/provider")
async def provider_webhook(
    request: Request,
    x_webhook_secret: str | None = Header(None),
):
    """Ingress for Instagram lifecycle events from the upstream provider."""
    settings = get_settings()
    if settings.zernio_webhook_secret and x_webhook_secret != settings.zernio_webhook_secret:
        return {"ok": False}

    raw = await request.json()
    event = normalize_webhook_event(raw)
    container = request.app.state.container

    # Best-effort: resolve tenant from account id in payload
    account_ext = (
        (event.get("payload") or {}).get("account_id")
        or (event.get("payload") or {}).get("accountId")
    )
    async with container.session_factory() as session:
        tenant_callback = None
        if account_ext:
            from sqlalchemy import select

            from social_hub.infrastructure.db.models.social_account import SocialAccountModel

            stmt = select(SocialAccountModel).where(
                SocialAccountModel.external_account_id == str(account_ext),
                SocialAccountModel.platform == PlatformType.INSTAGRAM.value,
            )
            acc = await session.scalar(stmt)
            if acc:
                tenant = await SQLAlchemyTenantRepo(session).get_by_id(acc.tenant_id)
                if tenant:
                    tenant_callback = tenant.webhook_callback_url
                    event["tenant_id"] = str(tenant.id)
                    event["account_id"] = str(acc.id)

    if tenant_callback:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(tenant_callback, json=event)
        except Exception as exc:
            logger.warning("tenant_webhook_forward_failed", error=str(exc))

    return {"ok": True}


@router.post("/webhooks/social/{platform}/{account_id}")
async def platform_webhook(
    platform: str,
    account_id: UUID,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
    x_webhook_secret: str | None = Header(None),
):
    """Ingress for Telegram/Bale bot updates."""
    container = request.app.state.container
    body = await request.body()
    raw = await request.json()

    async with container.session_factory() as session:
        async with session.begin():
            account = await SQLAlchemySocialAccountRepo(session).get_by_id_unscoped(account_id)
            if account is None or account.platform.value != platform:
                return {"ok": False}

            secret = account.settings.get("webhook_secret")
            driver = None
            if platform == "telegram":
                from social_hub.infrastructure.platforms.telegram.driver import TelegramDriver

                driver = TelegramDriver()
                headers = {
                    "X-Telegram-Bot-Api-Secret-Token": x_telegram_bot_api_secret_token or ""
                }
                if not driver.verify_webhook(headers, body, secret):
                    return {"ok": False}
            elif platform == "bale":
                from social_hub.infrastructure.platforms.bale.driver import BaleDriver

                driver = BaleDriver()
                headers = {"X-Webhook-Secret": x_webhook_secret or ""}
                if not driver.verify_webhook(headers, body, secret):
                    return {"ok": False}
            else:
                return {"ok": True}

            incoming = driver.parse_incoming(raw)
            if incoming and getattr(incoming, "event_type", None):
                credentials = {}
                if account.credentials_encrypted:
                    credentials = container.encryptor.decrypt(
                        bytes(account.credentials_encrypted)
                    )
                await container.arq_redis.enqueue_job(
                    "process_interaction_job",
                    {
                        "tenant_id": str(account.tenant_id),
                        "connection_id": str(account.id),
                        "platform_type": platform,
                        "credentials": credentials,
                        "connection_settings": account.settings,
                        "incoming": {
                            "event_type": getattr(incoming.event_type, "value", str(incoming.event_type)),
                            "user_ref": incoming.user_ref,
                            "raw": incoming.raw,
                            "button_short_id": getattr(incoming, "button_short_id", None),
                            "reply_chat_id": getattr(incoming, "reply_chat_id", None),
                            "reply_message_id": getattr(incoming, "reply_message_id", None),
                            "callback_query_id": getattr(incoming, "callback_query_id", None),
                        },
                    },
                )

    return {"ok": True}
