"""Shared helpers for Telegram/Bale/Eitaa credential-based adapters."""

from uuid import uuid4

from social_hub.application.adapters.base import (
    ConnectStartResult,
    CreatePostRequest,
    PlatformAdapter,
    PlatformPostResult,
)
from social_hub.config import Settings
from social_hub.domain.entities.social_account import SocialAccount
from social_hub.domain.exceptions import InvalidCredentialsError
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.social_capabilities import SocialCapabilities
from social_hub.infrastructure.db.repositories.social_account_repo import (
    SQLAlchemySocialAccountRepo,
)
from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.domain.value_objects.media_ref import MediaRef
from social_hub.infrastructure.platforms.dto.outgoing_button import OutgoingButton
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost
from social_hub.infrastructure.platforms.telegram.button_encoder import make_callback_data
from social_hub.shared.types import TenantContext


class BotPlatformAdapter(PlatformAdapter):
    """Credential-direct connect + publish via existing platform drivers."""

    def __init__(
        self,
        *,
        platform: PlatformType,
        capabilities: SocialCapabilities,
        driver,
        account_repo: SQLAlchemySocialAccountRepo,
        encryptor: FernetEncryptor,
        settings: Settings,
    ) -> None:
        self._platform = platform
        self._capabilities = capabilities
        self._driver = driver
        self._account_repo = account_repo
        self._encryptor = encryptor
        self._settings = settings

    @property
    def platform(self) -> PlatformType:
        return self._platform

    @property
    def capabilities(self) -> SocialCapabilities:
        return self._capabilities

    async def connect_start(
        self,
        tenant_ctx: TenantContext,
        *,
        redirect_url: str | None = None,
        login_method: str | None = None,
        mode: str | None = None,
        credentials: dict | None = None,
        settings: dict | None = None,
    ) -> ConnectStartResult:
        if not credentials or not credentials.get("bot_token"):
            raise InvalidCredentialsError("credentials.bot_token is required")
        settings = settings or {}
        if "channel_id" not in settings:
            raise InvalidCredentialsError("settings.channel_id is required")

        encrypted = self._encryptor.encrypt(credentials)
        external_id = credentials.get("bot_id") or f"{self._platform.value}:{uuid4().hex[:12]}"
        account = SocialAccount.create(
            tenant_id=tenant_ctx.tenant_id,
            platform=self._platform,
            external_account_id=str(external_id),
            credentials_encrypted=encrypted,
            settings=settings,
            display_name=settings.get("title") or settings.get("channel_id"),
            username=str(settings.get("channel_id")),
        )
        account = await self._account_repo.create(account)
        return ConnectStartResult(account=account, mode="credentials")

    async def disconnect(self, account: SocialAccount) -> None:
        await self._account_repo.delete(account.tenant_id, account.id)

    async def create_post(
        self,
        tenant_ctx: TenantContext,
        account: SocialAccount,
        request: CreatePostRequest,
        credentials: dict | None = None,
    ) -> PlatformPostResult:
        creds = credentials or (
            self._encryptor.decrypt(account.credentials_encrypted)
            if account.credentials_encrypted
            else {}
        )
        # Build a minimal connection-like object for legacy drivers
        from social_hub.domain.entities.platform_connection import PlatformConnection

        fake_conn = PlatformConnection(
            id=account.id,
            tenant_id=account.tenant_id,
            platform_type=account.platform,
            credentials_encrypted=account.credentials_encrypted or b"",
            settings=account.settings,
            is_active=account.is_active,
        )
        ctx = ConnectionContext(connection=fake_conn, credentials=creds)

        text_parts = []
        if request.title:
            text_parts.append(f"<b>{request.title}</b>")
        if request.content:
            text_parts.append(request.content)
        if request.price is not None:
            cur = request.currency or ""
            text_parts.append(f"{request.price} {cur}".strip())
        text = "\n".join(text_parts) or (request.content or "")

        media = [MediaRef(url=m.url, sort_order=i) for i, m in enumerate(request.media_items)]
        outgoing_buttons: list[OutgoingButton] = []
        for b in request.buttons:
            if b.get("action") == "url" and (b.get("payload") or {}).get("url"):
                outgoing_buttons.append(
                    OutgoingButton(label=b.get("label", ""), url=b["payload"]["url"])
                )
            elif b.get("short_id"):
                outgoing_buttons.append(
                    OutgoingButton(
                        label=b.get("label", ""),
                        callback_data=make_callback_data(b["short_id"]),
                    )
                )
        button_rows = [outgoing_buttons[i : i + 2] for i in range(0, len(outgoing_buttons), 2)]
        outgoing = OutgoingPost(text=text, media=media, buttons=button_rows)
        result = await self._driver.publish(ctx, outgoing)
        if result.success:
            return PlatformPostResult(
                account_id=account.id,
                platform=self._platform.value,
                status="published",
                platform_message_id=result.platform_message_id,
            )
        return PlatformPostResult(
            account_id=account.id,
            platform=self._platform.value,
            status="failed",
            error=result.error_message,
        )

    async def test_connection(self, account: SocialAccount, credentials: dict) -> dict:
        token = credentials.get("bot_token")
        if not token:
            return {"ok": False, "error": "credentials.bot_token is required"}
        if self._platform == PlatformType.TELEGRAM:
            from social_hub.infrastructure.platforms.telegram.client import TelegramClient

            me = await TelegramClient(token).get_me()
            return {"ok": True, "bot": me}
        if self._platform == PlatformType.BALE:
            from social_hub.infrastructure.platforms.bale.client import BaleClient

            me = await BaleClient(token).get_me()
            return {"ok": True, "bot": me}
        if self._platform == PlatformType.EITAA:
            from social_hub.infrastructure.platforms.eitaa.client import EitaaClient

            me = await EitaaClient(token).get_me()
            return {"ok": True, "bot": me}
        return {"ok": True}
