from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.application.services.capability_resolver import CapabilityResolver
from social_hub.application.services.connection_service import ConnectionService
from social_hub.application.services.delete_service import DeleteService
from social_hub.application.services.edit_service import EditService
from social_hub.application.services.publish_service import PublishService
from social_hub.application.services.tenant_service import TenantService
from social_hub.domain.exceptions import InvalidApiKeyError
from social_hub.infrastructure.db.repositories.button_repo import SQLAlchemyButtonRepo
from social_hub.infrastructure.db.repositories.connection_repo import SQLAlchemyConnectionRepo
from social_hub.infrastructure.db.repositories.interaction_event_repo import (
    SQLAlchemyInteractionEventRepo,
)
from social_hub.infrastructure.db.repositories.platform_message_repo import (
    SQLAlchemyPlatformMessageRepo,
)
from social_hub.infrastructure.db.repositories.post_repo import SQLAlchemyPostRepo
from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo
from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo
from social_hub.shared.types import TenantContext


async def get_session(request: Request):
    container = request.app.state.container
    async with container.session_factory() as session:
        async with session.begin():
            yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_tenant_repo(session: SessionDep):
    return SQLAlchemyTenantRepo(session)


def get_post_repo(session: SessionDep):
    return SQLAlchemyPostRepo(session)


def get_connection_repo(session: SessionDep):
    return SQLAlchemyConnectionRepo(session)


def get_publication_repo(session: SessionDep):
    return SQLAlchemyPublicationRepo(session)


def get_button_repo(session: SessionDep):
    return SQLAlchemyButtonRepo(session)


def get_platform_message_repo(session: SessionDep):
    return SQLAlchemyPlatformMessageRepo(session)


def get_interaction_event_repo(session: SessionDep):
    return SQLAlchemyInteractionEventRepo(session)


async def get_tenant_context(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> TenantContext:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    container = request.app.state.container
    async with container.session_factory() as session:
        tenant_repo = SQLAlchemyTenantRepo(session)
        from social_hub.shared.utils import hash_api_key
        tenant = await tenant_repo.get_by_api_key_hash(hash_api_key(x_api_key))

    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )
    return TenantContext(tenant_id=tenant.id, tenant_name=tenant.name)


TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


def get_publish_service(
    request: Request,
    session: SessionDep,
    tenant_ctx: TenantContextDep,
) -> PublishService:
    container = request.app.state.container
    return PublishService(
        post_repo=SQLAlchemyPostRepo(session),
        connection_repo=SQLAlchemyConnectionRepo(session),
        publication_repo=SQLAlchemyPublicationRepo(session),
        button_repo=SQLAlchemyButtonRepo(session),
        capability_resolver=CapabilityResolver(),
        arq_pool=container.arq_redis,
    )


def get_connection_service(
    request: Request,
    session: SessionDep,
) -> ConnectionService:
    container = request.app.state.container
    return ConnectionService(
        connection_repo=SQLAlchemyConnectionRepo(session),
        encryptor=container.encryptor,
    )


def get_edit_service(
    request: Request,
    session: SessionDep,
) -> EditService:
    container = request.app.state.container
    return EditService(
        post_repo=SQLAlchemyPostRepo(session),
        publication_repo=SQLAlchemyPublicationRepo(session),
        capability_resolver=CapabilityResolver(),
        arq_pool=container.arq_redis,
    )


def get_delete_service(
    request: Request,
    session: SessionDep,
) -> DeleteService:
    container = request.app.state.container
    return DeleteService(
        post_repo=SQLAlchemyPostRepo(session),
        publication_repo=SQLAlchemyPublicationRepo(session),
        arq_pool=container.arq_redis,
    )


def get_tenant_service(session: SessionDep) -> TenantService:
    return TenantService(tenant_repo=SQLAlchemyTenantRepo(session))
