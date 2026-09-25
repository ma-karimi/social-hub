from uuid import UUID

from social_hub.application.adapters.base import ConnectStartResult, PageOption
from social_hub.application.adapters.registry import PlatformAdapterRegistry
from social_hub.domain.entities.social_account import SocialAccount
from social_hub.domain.exceptions import AccountNotFoundError
from social_hub.domain.value_objects.facebook_features import (
    DEFAULT_FACEBOOK_LOGIN_FEATURES,
    resolve_facebook_login_features,
)
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.repositories.social_account_repo import (
    SQLAlchemySocialAccountRepo,
)
from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo
from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor
from social_hub.shared.types import TenantContext


class SocialAccountService:
    def __init__(
        self,
        account_repo: SQLAlchemySocialAccountRepo,
        tenant_repo: SQLAlchemyTenantRepo,
        adapter_registry: PlatformAdapterRegistry,
        encryptor: FernetEncryptor,
    ) -> None:
        self._accounts = account_repo
        self._tenants = tenant_repo
        self._adapters = adapter_registry
        self._encryptor = encryptor

    async def connect(
        self,
        tenant_ctx: TenantContext,
        platform: PlatformType,
        *,
        redirect_url: str | None = None,
        login_method: str | None = None,
        mode: str | None = None,
        credentials: dict | None = None,
        settings: dict | None = None,
    ) -> ConnectStartResult:
        adapter = self._adapters.get(platform)
        return await adapter.connect_start(
            tenant_ctx,
            redirect_url=redirect_url,
            login_method=login_method,
            mode=mode,
            credentials=credentials,
            settings=settings,
        )

    async def list_pages(self, platform: PlatformType, connect_token: str) -> list[PageOption]:
        adapter = self._adapters.get(platform)
        return await adapter.connect_list_pages(connect_token)

    async def select_page(
        self, platform: PlatformType, connect_token: str, page_id: str
    ) -> SocialAccount:
        adapter = self._adapters.get(platform)
        return await adapter.connect_select(connect_token, page_id)

    async def list_accounts(
        self, tenant_ctx: TenantContext, platform: PlatformType | None = None
    ) -> list[SocialAccount]:
        return await self._accounts.list_by_tenant(tenant_ctx.tenant_id, platform)

    async def get_account(self, tenant_ctx: TenantContext, account_id: UUID) -> SocialAccount:
        account = await self._accounts.get_by_id(tenant_ctx.tenant_id, account_id)
        if account is None:
            raise AccountNotFoundError()
        return account

    async def update_account(
        self,
        tenant_ctx: TenantContext,
        account_id: UUID,
        *,
        settings: dict | None = None,
        credentials: dict | None = None,
        is_active: bool | None = None,
    ) -> SocialAccount:
        account = await self.get_account(tenant_ctx, account_id)
        if settings is not None:
            account.settings = {**account.settings, **settings}
        if credentials is not None:
            account.credentials_encrypted = self._encryptor.encrypt(credentials)
        if is_active is not None:
            account.is_active = is_active
        return await self._accounts.update(account)

    async def delete_account(self, tenant_ctx: TenantContext, account_id: UUID) -> None:
        account = await self.get_account(tenant_ctx, account_id)
        adapter = self._adapters.get(account.platform)
        await adapter.disconnect(account)

    async def test_account(self, tenant_ctx: TenantContext, account_id: UUID) -> dict:
        account = await self.get_account(tenant_ctx, account_id)
        creds = {}
        if account.credentials_encrypted:
            creds = self._encryptor.decrypt(account.credentials_encrypted)
        adapter = self._adapters.get(account.platform)
        return await adapter.test_connection(account, creds)

    async def publishing_quota(self, tenant_ctx: TenantContext, account_id: UUID) -> dict:
        account = await self.get_account(tenant_ctx, account_id)
        adapter = self._adapters.get(account.platform)
        return await adapter.get_publishing_quota(account, "")

    async def get_platform_config(self, tenant_ctx: TenantContext, platform: str) -> dict:
        tenant = await self._tenants.get_by_id(tenant_ctx.tenant_id)
        settings = tenant.settings if tenant else {}
        if platform == "instagram":
            return {"facebook_login_features": resolve_facebook_login_features(settings)}
        return {}

    async def set_platform_config(
        self, tenant_ctx: TenantContext, platform: str, body: dict
    ) -> dict:
        tenant = await self._tenants.get_by_id(tenant_ctx.tenant_id)
        if tenant is None:
            raise AccountNotFoundError("Tenant not found")
        settings = dict(tenant.settings or {})
        social = dict(settings.get("social") or {})
        if platform == "instagram":
            current = resolve_facebook_login_features(settings)
            incoming = body.get("facebook_login_features") or {}
            merged = {**DEFAULT_FACEBOOK_LOGIN_FEATURES, **current, **incoming}
            social["instagram"] = {
                **(social.get("instagram") or {}),
                "facebook_login_features": {k: bool(v) for k, v in merged.items()},
            }
            settings["social"] = social
            tenant.settings = settings
            await self._tenants.update(tenant)
            return {"facebook_login_features": merged}
        return body
