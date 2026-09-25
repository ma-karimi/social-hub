from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from social_hub.api.deps import TenantContextDep, raise_social_error
from social_hub.api.i18n import resolve_locale
from social_hub.api.schemas.social import MediaPresignRequest, MediaPresignResponse
from social_hub.config import get_settings
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import SocialHubError
from social_hub.infrastructure.db.repositories.social_aux_repos import (
    SQLAlchemyMediaRelayRepo,
    SQLAlchemyProviderCredentialRepo,
)
from social_hub.infrastructure.providers.zernio.client import ZernioHttpClient
from social_hub.infrastructure.providers.zernio.key_resolver import ProviderKeyResolver
from social_hub.infrastructure.providers.zernio.mappers import (
    contains_zernio_domain,
    map_presign_response,
)
from social_hub.infrastructure.providers.zernio.media_relay import stream_upstream

router = APIRouter(tags=["social-media"])


@router.post("/media/presign", response_model=MediaPresignResponse)
async def media_presign(
    body: MediaPresignRequest,
    request: Request,
    tenant_ctx: TenantContextDep,
    accept_language: Annotated[str | None, Header()] = None,
):
    locale = resolve_locale(accept_language)
    settings = get_settings()
    container = request.app.state.container
    async with container.session_factory() as session:
        async with session.begin():
            resolver = ProviderKeyResolver(
                settings, container.encryptor, SQLAlchemyProviderCredentialRepo(session)
            )
            creds = await resolver.resolve(tenant_ctx.tenant_id)
            if not creds.api_key:
                raise_social_error(ErrorCode.UPSTREAM_ERROR, locale=locale)
            client = ZernioHttpClient(creds.api_key, creds.base_url)
            try:
                upstream = await client.media_presign(body.filename, body.content_type)
            except SocialHubError as exc:
                raise_social_error(exc.error_code, locale=locale, exc=exc)

            payload, opaque_key, upstream_public = map_presign_response(
                upstream,
                relay_base_url=settings.media_relay_base or str(request.base_url).rstrip("/"),
            )
            if contains_zernio_domain(payload["public_url"]):
                raise_social_error(ErrorCode.INTERNAL_ERROR, locale=locale)

            from urllib.parse import urlparse

            path = urlparse(upstream_public).path if upstream_public.startswith("http") else upstream_public
            relay_repo = SQLAlchemyMediaRelayRepo(session)
            await relay_repo.create(
                opaque_key=opaque_key,
                upstream_path=path.lstrip("/") if isinstance(path, str) else "",
                upstream_public_url=upstream_public
                if upstream_public.startswith("http")
                else f"{creds.media_cdn_base}/{path.lstrip('/')}",
                tenant_id=tenant_ctx.tenant_id,
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=int(payload.get("expires_in") or 3600)),
            )

    # Ensure upload_url doesn't advertise zernio brand in public docs — runtime may be S3
    return MediaPresignResponse(**payload)


@router.get("/media/relay/{key}")
async def media_relay(key: str, request: Request):
    container = request.app.state.container
    async with container.session_factory() as session:
        relay_repo = SQLAlchemyMediaRelayRepo(session)
        row = await relay_repo.get_by_opaque_key(key)
        if row is None:
            raise_social_error(ErrorCode.NOT_FOUND, locale="en")
        url = row.upstream_public_url
    return await stream_upstream(url)
