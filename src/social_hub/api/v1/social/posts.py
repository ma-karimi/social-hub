from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response

from social_hub.api.deps import TenantContextDep, get_social_post_service, raise_social_error
from social_hub.api.i18n import resolve_locale
from social_hub.api.schemas.social import (
    CreateSocialPostRequest,
    PlatformResultSchema,
    SocialPostResponse,
)
from social_hub.application.services.social_post_service import SocialPostService
from social_hub.domain.exceptions import SocialHubError

router = APIRouter(tags=["social-posts"])


@router.post("/posts", response_model=SocialPostResponse)
async def create_post(
    body: CreateSocialPostRequest,
    response: Response,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialPostService, Depends(get_social_post_service)],
    accept_language: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        result = await service.create_post(
            tenant_ctx,
            account_ids=[UUID(a) for a in body.account_ids],
            content=body.content,
            title=body.title,
            media_items=[m.model_dump() for m in body.media_items],
            publish_now=body.publish_now,
            scheduled_for=body.scheduled_for,
            is_draft=body.is_draft,
            timezone=body.timezone or "Asia/Tehran",
            platform_specific_data=(
                body.platform_specific_data.model_dump(exclude_none=True)
                if body.platform_specific_data
                else None
            ),
            metadata=body.metadata,
            external_ref=body.external_ref,
            price=body.price,
            currency=body.currency,
            buttons=[b.model_dump() for b in body.buttons],
            request_id=x_request_id,
        )
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)

    response.status_code = result.http_status
    return SocialPostResponse(
        post_id=str(result.post_id),
        status=result.status,
        platforms=[
            PlatformResultSchema(
                account_id=str(p.account_id),
                platform=p.platform,
                status=p.status,
                platform_post_url=p.platform_post_url,
                platform_message_id=p.platform_message_id,
                error=p.error,
            )
            for p in result.platforms
        ],
        warnings=result.warnings,
    )


@router.get("/posts")
async def list_posts(
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialPostService, Depends(get_social_post_service)],
    limit: int = 50,
    offset: int = 0,
):
    return await service.list_posts(tenant_ctx, limit=limit, offset=offset)


@router.get("/posts/{post_id}")
async def get_post(
    post_id: UUID,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialPostService, Depends(get_social_post_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        return await service.get_post(tenant_ctx, post_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: UUID,
    tenant_ctx: TenantContextDep,
    service: Annotated[SocialPostService, Depends(get_social_post_service)],
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    try:
        await service.delete_post(tenant_ctx, post_id)
    except SocialHubError as exc:
        raise_social_error(exc.error_code, locale=locale, exc=exc)
