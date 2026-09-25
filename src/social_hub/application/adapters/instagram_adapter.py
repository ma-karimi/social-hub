"""Instagram PlatformAdapter backed by upstream HTTP client (internal)."""

from uuid import UUID

import structlog

from social_hub.application.adapters.base import (
    ConnectStartResult,
    CreatePostRequest,
    PageOption,
    PlatformAdapter,
    PlatformPostResult,
)
from social_hub.application.adapters.capabilities import SOCIAL_CAPABILITIES
from social_hub.application.services.facebook_feature_gate import (
    assert_facebook_feature_allowed,
    collect_fb_gated_fields,
)
from social_hub.config import Settings
from social_hub.domain.entities.connect_session import ConnectSession
from social_hub.domain.entities.social_account import SocialAccount
from social_hub.domain.exceptions import (
    ConnectTokenExpiredError,
    InvalidConnectTokenError,
    SocialHubError,
)
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.social_capabilities import SocialCapabilities
from social_hub.infrastructure.db.repositories.social_account_repo import (
    SQLAlchemySocialAccountRepo,
)
from social_hub.infrastructure.db.repositories.social_aux_repos import (
    SQLAlchemyConnectSessionRepo,
)
from social_hub.infrastructure.providers.zernio.client import ZernioHttpClient
from social_hub.infrastructure.providers.zernio.key_resolver import ProviderKeyResolver
from social_hub.infrastructure.providers.zernio.mappers import (
    map_post_response,
    map_quota,
    platform_specific_to_upstream,
)
from social_hub.shared.types import TenantContext

logger = structlog.get_logger(__name__)


class InstagramAdapter(PlatformAdapter):
    def __init__(
        self,
        *,
        settings: Settings,
        key_resolver: ProviderKeyResolver,
        account_repo: SQLAlchemySocialAccountRepo,
        connect_session_repo: SQLAlchemyConnectSessionRepo,
        tenant_settings_provider=None,
    ) -> None:
        self._settings = settings
        self._key_resolver = key_resolver
        self._account_repo = account_repo
        self._sessions = connect_session_repo
        self._tenant_settings_provider = tenant_settings_provider

    @property
    def platform(self) -> PlatformType:
        return PlatformType.INSTAGRAM

    @property
    def capabilities(self) -> SocialCapabilities:
        return SOCIAL_CAPABILITIES[PlatformType.INSTAGRAM]

    async def _client_for(self, tenant_id: UUID) -> tuple[ZernioHttpClient, object]:
        creds = await self._key_resolver.resolve(tenant_id)
        if not creds.api_key:
            raise SocialHubError(
                "Upstream API key is not configured",
                error_code=ErrorCode.UPSTREAM_ERROR,
            )
        return ZernioHttpClient(creds.api_key, creds.base_url), creds

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
        if not redirect_url:
            raise SocialHubError(
                "redirect_url is required", error_code=ErrorCode.VALIDATION_ERROR
            )
        login_method = login_method or "instagram_login"
        mode = mode or "headless"
        headless = mode != "standard"

        client, provider = await self._client_for(tenant_ctx.tenant_id)
        if not provider.profile_id:
            raise SocialHubError(
                "Provider profile is not configured",
                error_code=ErrorCode.UPSTREAM_ERROR,
            )

        session = ConnectSession.create(
            tenant_id=tenant_ctx.tenant_id,
            platform=self.platform.value,
            consumer_redirect_url=redirect_url,
            login_method=login_method,
            mode=mode,
        )
        await self._sessions.create(session)

        callback = (
            f"{self._settings.connect_callback_base}"
            f"/api/v1/social/accounts/connect/callback"
            f"?session={session.our_connect_token}"
        )
        data = await client.connect_instagram(
            provider.profile_id,
            callback,
            login_method=login_method,
            headless=headless,
        )
        auth_url = data.get("authUrl") or data.get("auth_url")
        return ConnectStartResult(auth_url=auth_url, mode=mode)

    async def handle_oauth_callback(
        self,
        session_token: str,
        *,
        upstream_connect_token: str | None = None,
        account_payload: dict | None = None,
    ) -> str:
        """Complete OAuth redirect; returns consumer redirect URL with our connect_token."""
        session = await self._sessions.get_by_token(session_token)
        if session is None:
            raise InvalidConnectTokenError("Invalid connect session")
        if session.is_expired:
            raise ConnectTokenExpiredError("Connect session expired")

        if upstream_connect_token:
            session.upstream_connect_token = upstream_connect_token
            await self._sessions.update(session)
            sep = "&" if "?" in session.consumer_redirect_url else "?"
            return (
                f"{session.consumer_redirect_url}{sep}"
                f"connect_token={session.our_connect_token}"
            )

        # Standard mode: account already connected upstream
        if account_payload:
            ext_id = str(
                account_payload.get("accountId")
                or account_payload.get("_id")
                or account_payload.get("id")
            )
            account = SocialAccount.create(
                tenant_id=session.tenant_id,
                platform=PlatformType.INSTAGRAM,
                external_account_id=ext_id,
                login_method=session.login_method,
                display_name=account_payload.get("name") or account_payload.get("displayName"),
                username=account_payload.get("username"),
                metadata=account_payload,
            )
            await self._account_repo.create(account)
            sep = "&" if "?" in session.consumer_redirect_url else "?"
            return (
                f"{session.consumer_redirect_url}{sep}"
                f"account_id={account.id}&status=connected"
            )

        sep = "&" if "?" in session.consumer_redirect_url else "?"
        return (
            f"{session.consumer_redirect_url}{sep}"
            f"connect_token={session.our_connect_token}"
        )

    async def connect_list_pages(self, connect_token: str) -> list[PageOption]:
        session = await self._require_session(connect_token)
        if not session.upstream_connect_token:
            raise InvalidConnectTokenError("Upstream connect token missing")
        client, _ = await self._client_for(session.tenant_id)
        data = await client.list_connect_pages(session.upstream_connect_token)
        pages = data.get("pages") or data.get("data") or []
        return [
            PageOption(
                page_id=str(p.get("id") or p.get("pageId")),
                name=p.get("name") or p.get("pageName") or "",
                metadata=p,
            )
            for p in pages
        ]

    async def connect_select(self, connect_token: str, page_id: str) -> SocialAccount:
        session = await self._require_session(connect_token)
        if not session.upstream_connect_token:
            raise InvalidConnectTokenError("Upstream connect token missing")
        client, _ = await self._client_for(session.tenant_id)
        data = await client.select_connect_page(session.upstream_connect_token, page_id)
        account_data = data.get("account") or data
        ext_id = str(
            account_data.get("accountId")
            or account_data.get("_id")
            or account_data.get("id")
            or page_id
        )
        account = SocialAccount.create(
            tenant_id=session.tenant_id,
            platform=PlatformType.INSTAGRAM,
            external_account_id=ext_id,
            login_method=session.login_method,
            display_name=account_data.get("name") or account_data.get("displayName"),
            username=account_data.get("username"),
            metadata=account_data,
        )
        account = await self._account_repo.create(account)
        await self._sessions.delete(session.id)
        return account

    async def _require_session(self, connect_token: str) -> ConnectSession:
        session = await self._sessions.get_by_token(connect_token)
        if session is None:
            raise InvalidConnectTokenError()
        if session.is_expired:
            raise ConnectTokenExpiredError()
        return session

    async def disconnect(self, account: SocialAccount) -> None:
        await self._account_repo.delete(account.tenant_id, account.id)

    async def create_post(
        self,
        tenant_ctx: TenantContext,
        account: SocialAccount,
        request: CreatePostRequest,
        credentials: dict | None = None,
    ) -> PlatformPostResult:
        tenant_settings = {}
        if self._tenant_settings_provider:
            tenant_settings = await self._tenant_settings_provider(tenant_ctx.tenant_id)

        for feature in collect_fb_gated_fields(request.platform_specific_data):
            assert_facebook_feature_allowed(account, tenant_settings, feature)

        if not request.media_items and not request.is_draft:
            raise SocialHubError("Media is required", error_code=ErrorCode.MISSING_MEDIA)

        client, _ = await self._client_for(tenant_ctx.tenant_id)
        psd = platform_specific_to_upstream(request.platform_specific_data)
        payload = {
            "content": request.content or "",
            "mediaItems": [
                {"type": m.type or "image", "url": m.url} for m in request.media_items
            ],
            "platforms": [
                {
                    "platform": "instagram",
                    "accountId": account.external_account_id,
                    "platformSpecificData": psd or None,
                }
            ],
            "timezone": request.timezone or "Asia/Tehran",
        }
        # Remove None platformSpecificData
        if not psd:
            del payload["platforms"][0]["platformSpecificData"]

        if request.is_draft:
            payload["isDraft"] = True
        elif request.publish_now:
            payload["publishNow"] = True
        elif request.scheduled_for:
            payload["scheduledFor"] = request.scheduled_for

        if request.metadata:
            payload["metadata"] = request.metadata

        status, body = await client.create_post(payload, request_id=request.request_id)
        mapped = map_post_response(
            body, account_id_map={account.external_account_id: str(account.id)}
        )
        platforms = mapped.get("platforms") or []
        first = platforms[0] if platforms else {}
        post_status = first.get("status") or mapped.get("status") or "unknown"
        if status == 207 or post_status == "failed":
            return PlatformPostResult(
                account_id=account.id,
                platform="instagram",
                status="failed",
                error=first.get("error") or "Publishing failed",
                platform_post_url=first.get("platform_post_url"),
            )
        return PlatformPostResult(
            account_id=account.id,
            platform="instagram",
            status=post_status,
            platform_post_url=first.get("platform_post_url"),
            platform_message_id=mapped.get("id"),
        )

    async def get_publishing_quota(self, account: SocialAccount, api_key: str = "") -> dict:
        client, _ = await self._client_for(account.tenant_id)
        raw = await client.get_publishing_limit(account.external_account_id)
        return map_quota(raw)
