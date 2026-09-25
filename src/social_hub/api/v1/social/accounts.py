from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import RedirectResponse

from social_hub.api.deps import TenantContextDep, get_social_account_service, raise_social_error
from social_hub.api.i18n import resolve_locale
from social_hub.api.schemas.social import (
    ConnectAccountRequest,
    ConnectStartResponse,
    InstagramConfigResponse,
    InstagramConfigUpdateRequest,
    PageOptionResponse,
    PublishingQuotaResponse,
    SelectPageRequest,
    SocialAccountResponse,
    UpdateAccountRequest,
)
from social_hub.application.services.social_account_service import SocialAccountService
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import SocialHubError
from social_hub.domain.value_objects.platform_type import PlatformType

router = APIRouter(tags=["social-accounts"])


def _account_response(acc) -> SocialAccountResponse:
    return SocialAccountResponse(
        id=str(acc.id),
        tenant_id=str(acc.tenant_id),
        platform=acc.platform.value,
        external_account_id=acc.external_account_id,
        login_method=acc.login_method,
        display_name=acc.display_name,
        username=acc.username,
        settings=acc.settings,
        is_active=acc.is_active,
    )


@router.post("/accounts/connect", response_model=ConnectStartResponse)
async def connect_account(
    body: ConnectAccountRequest,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        platform = PlatformType(body.platform)
        result = await service.connect(
            tenant_ctx,
            platform,
            redirect_url=body.redirect_url,
            login_method=body.login_method,
            mode=body.mode,
            credentials=body.credentials,
            settings=body.settings,
        )
    except ValueError:
        raise_social_error(ErrorCode.PLATFORM_NOT_SUPPORTED, locale=locale)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)

    return ConnectStartResponse(
        auth_url=result.auth_url,
        account_id=str(result.account.id) if result.account else None,
        mode=result.mode,
    )


@router.get("/accounts/connect/callback")
async def connect_callback(
    request: Request,
    session: str,
    connect_token: str | None = None,
    account_id: str | None = None,
):
    """OAuth callback — never exposes upstream tokens to the consumer."""
    from social_hub.application.adapters.instagram_adapter import InstagramAdapter

    container = request.app.state.container
    adapter: InstagramAdapter = container.adapter_registry.get(PlatformType.INSTAGRAM)
    # Rebuild session-scoped adapter pieces via container helper if needed
    async with container.session_factory() as db:
        async with db.begin():
            from social_hub.infrastructure.db.repositories.social_account_repo import (
                SQLAlchemySocialAccountRepo,
            )
            from social_hub.infrastructure.db.repositories.social_aux_repos import (
                SQLAlchemyConnectSessionRepo,
                SQLAlchemyProviderCredentialRepo,
            )
            from social_hub.infrastructure.providers.zernio.key_resolver import (
                ProviderKeyResolver,
            )
            from social_hub.config import get_settings

            settings = get_settings()
            ig = InstagramAdapter(
                settings=settings,
                key_resolver=ProviderKeyResolver(
                    settings, container.encryptor, SQLAlchemyProviderCredentialRepo(db)
                ),
                account_repo=SQLAlchemySocialAccountRepo(db),
                connect_session_repo=SQLAlchemyConnectSessionRepo(db),
            )
            try:
                url = await ig.handle_oauth_callback(
                    session,
                    upstream_connect_token=connect_token,
                    account_payload={"id": account_id} if account_id else None,
                )
            except SocialHubError:
                return RedirectResponse(url="/?error=connect_failed", status_code=302)
    return RedirectResponse(url=url, status_code=302)


@router.get("/accounts/connect/pages", response_model=list[PageOptionResponse])
async def list_connect_pages(
    connect_token: str,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    platform: str = "instagram",
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        pages = await service.list_pages(PlatformType(platform), connect_token)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return [PageOptionResponse(page_id=p.page_id, name=p.name) for p in pages]


@router.post("/accounts/connect/select", response_model=SocialAccountResponse)
async def select_connect_page(
    body: SelectPageRequest,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        account = await service.select_page(
            PlatformType(body.platform), body.connect_token, body.page_id
        )
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _account_response(account)


@router.get("/accounts", response_model=list[SocialAccountResponse])
async def list_accounts(
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    platform: str | None = Query(None),
):
    plat = PlatformType(platform) if platform else None
    accounts = await service.list_accounts(tenant_ctx, plat)
    return [_account_response(a) for a in accounts]


@router.get("/accounts/{account_id}", response_model=SocialAccountResponse)
async def get_account(
    account_id: UUID,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        account = await service.get_account(tenant_ctx, account_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _account_response(account)


@router.patch("/accounts/{account_id}", response_model=SocialAccountResponse)
async def update_account(
    account_id: UUID,
    body: UpdateAccountRequest,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        account = await service.update_account(
            tenant_ctx,
            account_id,
            settings=body.settings,
            credentials=body.credentials,
            is_active=body.is_active,
        )
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _account_response(account)


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: UUID,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        await service.delete_account(tenant_ctx, account_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)


@router.post("/accounts/{account_id}/test")
async def test_account(
    account_id: UUID,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
):
    return await service.test_account(tenant_ctx, account_id)


@router.get(
    "/accounts/{account_id}/publishing-quota",
    response_model=PublishingQuotaResponse,
)
async def publishing_quota(
    account_id: UUID,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        data = await service.publishing_quota(tenant_ctx, account_id)
    except NotImplementedError:
        raise_social_error(ErrorCode.CAPABILITY_NOT_SUPPORTED, locale=locale)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return PublishingQuotaResponse(**data)


@router.get("/config/{platform}", response_model=InstagramConfigResponse)
async def get_config(
    platform: str,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
):
    data = await service.get_platform_config(tenant_ctx, platform)
    return InstagramConfigResponse(**data)


@router.patch("/config/{platform}", response_model=InstagramConfigResponse)
async def patch_config(
    platform: str,
    body: InstagramConfigUpdateRequest,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
):
    data = await service.set_platform_config(
        tenant_ctx, platform, body.model_dump(exclude_none=True)
    )
    return InstagramConfigResponse(**data)
