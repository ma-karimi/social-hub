from typing import Annotated, NoReturn

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.api.i18n import error_body, error_from_exception, resolve_locale, status_for_code
from social_hub.application.services.social_account_service import SocialAccountService
from social_hub.application.services.social_post_service import SocialPostService
from social_hub.application.services.tenant_service import TenantService
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import SocialHubError
from social_hub.infrastructure.db.repositories.button_repo import SQLAlchemyButtonRepo
from social_hub.infrastructure.db.repositories.post_repo import SQLAlchemyPostRepo
from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo
from social_hub.infrastructure.db.repositories.social_account_repo import (
    SQLAlchemySocialAccountRepo,
)
from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo
from social_hub.shared.types import TenantContext


async def get_session(request: Request):
    container = request.app.state.container
    async with container.session_factory() as session:
        async with session.begin():
            yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def raise_social_error(
    error_code: ErrorCode | str,
    *,
    locale: str = "en",
    exc: Exception | None = None,
) -> NoReturn:
    if isinstance(exc, SocialHubError):
        raise exc
    code = ErrorCode(error_code) if not isinstance(error_code, ErrorCode) else error_code
    raise SocialHubError(error_code=code)


async def get_tenant_context(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> TenantContext:
    locale = resolve_locale(request.headers.get("accept-language"))
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_body(ErrorCode.UNAUTHORIZED, locale=locale),
        )
    container = request.app.state.container
    async with container.session_factory() as session:
        tenant_repo = SQLAlchemyTenantRepo(session)
        from social_hub.shared.utils import hash_api_key

        tenant = await tenant_repo.get_by_api_key_hash(hash_api_key(x_api_key))

    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_body(ErrorCode.UNAUTHORIZED, locale=locale),
        )
    return TenantContext(tenant_id=tenant.id, tenant_name=tenant.name)


TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


def get_social_account_service(
    request: Request,
    session: SessionDep,
) -> SocialAccountService:
    container = request.app.state.container
    registry = container.adapter_registry
    if hasattr(registry, "bind_session"):
        registry.bind_session(session)
    return SocialAccountService(
        account_repo=SQLAlchemySocialAccountRepo(session),
        tenant_repo=SQLAlchemyTenantRepo(session),
        adapter_registry=registry,
        encryptor=container.encryptor,
    )


def get_social_post_service(
    request: Request,
    session: SessionDep,
) -> SocialPostService:
    container = request.app.state.container
    registry = container.adapter_registry
    if hasattr(registry, "bind_session"):
        registry.bind_session(session)
    return SocialPostService(
        post_repo=SQLAlchemyPostRepo(session),
        account_repo=SQLAlchemySocialAccountRepo(session),
        publication_repo=SQLAlchemyPublicationRepo(session),
        button_repo=SQLAlchemyButtonRepo(session),
        adapter_registry=registry,
        encryptor=container.encryptor,
        arq_pool=container.arq_redis,
    )


def get_tenant_service(session: SessionDep) -> TenantService:
    return TenantService(tenant_repo=SQLAlchemyTenantRepo(session))


def get_instagram_upstream(request: Request):
    return None
