"""Instagram inbox, analytics, automations — proxied via internal upstream client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from social_hub.api.deps import TenantContextDep, get_social_account_service, raise_social_error
from social_hub.api.i18n import resolve_locale
from social_hub.api.schemas.social import IceBreakersRequest
from social_hub.application.services.facebook_feature_gate import assert_facebook_feature_allowed
from social_hub.application.services.social_account_service import SocialAccountService
from social_hub.config import get_settings
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import SocialHubError
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.repositories.social_aux_repos import (
    SQLAlchemyProviderCredentialRepo,
)
from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo
from social_hub.infrastructure.providers.zernio.client import ZernioHttpClient
from social_hub.infrastructure.providers.zernio.key_resolver import ProviderKeyResolver
from social_hub.infrastructure.providers.zernio.mappers import keys_to_snake, scrub_urls_in_obj

router = APIRouter(tags=["social-instagram"])


async def _ig_client(request: Request, tenant_id: UUID) -> ZernioHttpClient:
    settings = get_settings()
    container = request.app.state.container
    async with container.session_factory() as session:
        resolver = ProviderKeyResolver(
            settings, container.encryptor, SQLAlchemyProviderCredentialRepo(session)
        )
        creds = await resolver.resolve(tenant_id)
    if not creds.api_key:
        raise SocialHubError("Upstream not configured", error_code=ErrorCode.UPSTREAM_ERROR)
    return ZernioHttpClient(creds.api_key, creds.base_url)


async def _account_external(
    service: SocialAccountService, tenant_ctx, account_id: UUID
) -> tuple[Any, str]:
    account = await service.get_account(tenant_ctx, account_id)
    if account.platform != PlatformType.INSTAGRAM:
        raise SocialHubError(
            "Instagram account required", error_code=ErrorCode.CAPABILITY_NOT_SUPPORTED
        )
    return account, account.external_account_id


def _public(data: Any) -> Any:
    return keys_to_snake(scrub_urls_in_obj(data))


@router.get("/analytics")
async def analytics(
    request: Request,
    tenant_ctx: TenantContextDep,
    platform: str = "instagram",
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.get_analytics({"platform": platform})
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.get("/accounts/{account_id}/insights")
async def account_insights(
    account_id: UUID,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        _, ext = await _account_external(service, tenant_ctx, account_id)
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.get_account_insights(ext)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.get("/accounts/{account_id}/stories")
async def list_stories(
    account_id: UUID,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        _, ext = await _account_external(service, tenant_ctx, account_id)
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.list_stories(ext)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.get("/accounts/{account_id}/stories/{story_id}/insights")
async def story_insights(
    account_id: UUID,
    story_id: str,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        _, ext = await _account_external(service, tenant_ctx, account_id)
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.get_story_insights(ext, story_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.get("/accounts/{account_id}/audio")
async def search_audio(
    account_id: UUID,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    q: str | None = None,
    audio_type: str | None = Query(None, alias="audioType"),
    accept_language: Annotated[str | None, Header()] = None,
):
    """Search catalog audio. Requires Facebook Login connection."""
    locale = resolve_locale(accept_language)
    try:
        account, ext = await _account_external(service, tenant_ctx, account_id)
        container = request.app.state.container
        async with container.session_factory() as session:
            tenant = await SQLAlchemyTenantRepo(session).get_by_id(tenant_ctx.tenant_id)
            assert_facebook_feature_allowed(
                account, tenant.settings if tenant else {}, "audio_configuration"
            )
        client = await _ig_client(request, tenant_ctx.tenant_id)
        params = {}
        if q:
            params["q"] = q
        if audio_type:
            params["audioType"] = audio_type
        data = await client.search_audio(ext, params or None)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.get("/accounts/{account_id}/follow-status/{user_id}")
async def follow_status(
    account_id: UUID,
    user_id: str,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        _, ext = await _account_external(service, tenant_ctx, account_id)
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.get_follow_status(ext, user_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.get("/accounts/{account_id}/ice-breakers")
async def get_ice_breakers(
    account_id: UUID,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        _, ext = await _account_external(service, tenant_ctx, account_id)
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.get_ice_breakers(ext)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.put("/accounts/{account_id}/ice-breakers")
async def put_ice_breakers(
    account_id: UUID,
    body: IceBreakersRequest,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        _, ext = await _account_external(service, tenant_ctx, account_id)
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.put_ice_breakers(ext, body.ice_breakers)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.delete("/accounts/{account_id}/ice-breakers", status_code=204)
async def delete_ice_breakers(
    account_id: UUID,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        _, ext = await _account_external(service, tenant_ctx, account_id)
        client = await _ig_client(request, tenant_ctx.tenant_id)
        await client.delete_ice_breakers(ext)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)


# --- Inbox ---

@router.get("/inbox/conversations")
async def list_conversations(
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.list_conversations()
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.get("/inbox/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.get_conversation(conversation_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.post("/inbox/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.send_message(conversation_id, body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.post("/inbox/conversations/{conversation_id}/messages/{message_id}/reaction")
async def add_reaction(
    conversation_id: str,
    message_id: str,
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.add_reaction(conversation_id, message_id, body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.delete("/inbox/conversations/{conversation_id}/messages/{message_id}/reaction", status_code=204)
async def remove_reaction(
    conversation_id: str,
    message_id: str,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        await client.remove_reaction(conversation_id, message_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)


@router.get("/inbox/comments")
async def list_comments(
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.list_comments()
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.post("/inbox/comments")
async def create_comment(
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.create_comment(body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.post("/inbox/comments/{comment_id}/replies")
async def reply_comment(
    comment_id: str,
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.reply_comment(comment_id, body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.delete("/inbox/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        await client.delete_comment(comment_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)


@router.post("/inbox/comments/{comment_id}/hide")
async def hide_comment(
    comment_id: str,
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.hide_comment(comment_id, body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.post("/inbox/comments/{comment_id}/private-reply")
async def private_reply(
    comment_id: str,
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.private_reply_comment(comment_id, body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


# --- Automations ---

@router.get("/automations/comment-to-dm")
async def list_comment_automations(
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.list_comment_automations()
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.post("/automations/comment-to-dm")
async def create_comment_automation(
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.create_comment_automation(body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.put("/automations/comment-to-dm/{automation_id}")
async def update_comment_automation(
    automation_id: str,
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.update_comment_automation(automation_id, body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.delete("/automations/comment-to-dm/{automation_id}", status_code=204)
async def delete_comment_automation(
    automation_id: str,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        await client.delete_comment_automation(automation_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)


@router.get("/automations/story-reply")
async def list_story_reply_automations(
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.list_story_reply_automations()
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.post("/automations/story-reply")
async def create_story_reply_automation(
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.create_story_reply_automation(body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.put("/automations/story-reply/{automation_id}")
async def update_story_reply_automation(
    automation_id: str,
    body: dict,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.update_story_reply_automation(automation_id, body)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)


@router.delete("/automations/story-reply/{automation_id}", status_code=204)
async def delete_story_reply_automation(
    automation_id: str,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        client = await _ig_client(request, tenant_ctx.tenant_id)
        await client.delete_story_reply_automation(automation_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)


@router.post("/accounts/{account_id}/ads/connect")
async def connect_ads(
    account_id: UUID,
    request: Request,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialAccountService, Depends(get_social_account_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    """Connect ads for an Instagram account. Requires Facebook Login connection."""
    locale = resolve_locale(accept_language)
    try:
        account, _ = await _account_external(service, tenant_ctx, account_id)
        container = request.app.state.container
        async with container.session_factory() as session:
            tenant = await SQLAlchemyTenantRepo(session).get_by_id(tenant_ctx.tenant_id)
            assert_facebook_feature_allowed(account, tenant.settings if tenant else {}, "ads")
        client = await _ig_client(request, tenant_ctx.tenant_id)
        data = await client.connect_ads("instagram")
    except SocialHubError as exc:
        # Disabled features → 404 for ads endpoint per plan
        if exc.error_code == ErrorCode.FEATURE_DISABLED_FOR_TENANT:
            raise_social_error(ErrorCode.NOT_FOUND, locale=locale)
        raise_social_error(exc.error_code, locale=locale, exc=exc)
    return _public(data)
