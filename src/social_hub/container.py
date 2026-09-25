"""Composition root — wires all singletons together."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from social_hub.application.adapters.bot_adapter import BotPlatformAdapter
from social_hub.application.adapters.capabilities import SOCIAL_CAPABILITIES
from social_hub.application.adapters.instagram_adapter import InstagramAdapter
from social_hub.application.adapters.registry import PlatformAdapterRegistry
from social_hub.config import Settings
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.session import create_session_factory
from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor
from social_hub.infrastructure.platforms.bale.driver import BaleDriver
from social_hub.infrastructure.platforms.eitaa.driver import EitaaDriver
from social_hub.infrastructure.platforms.telegram.driver import TelegramDriver


@dataclass
class Container:
    session_factory: async_sessionmaker[AsyncSession]
    encryptor: FernetEncryptor
    adapter_registry: PlatformAdapterRegistry
    settings: Settings
    arq_redis: object


async def build_container(settings: Settings) -> Container:
    from arq import create_pool
    from arq.connections import RedisSettings

    session_factory = create_session_factory(settings.database_url)
    encryptor = FernetEncryptor(settings.encryption_key or _dev_key())

    # Adapters that need DB are constructed per-request in services;
    # registry holds prototype factories via lightweight wrappers created with a
    # session-less shell — Instagram/Bot adapters require repos, so we register
    # session-bound adapters lazily via a holder rebuilt in deps.
    # For container we store drivers + build a registry factory.
    adapter_registry = PlatformAdapterRegistry()

    # Placeholder registration happens in attach_adapters after first session —
    # instead register fully via a session-scoped rebuild helper.
    container = Container(
        session_factory=session_factory,
        encryptor=encryptor,
        adapter_registry=adapter_registry,
        settings=settings,
        arq_redis=await create_pool(RedisSettings.from_dsn(settings.redis_url)),
    )

    # Build adapters with a long-lived pattern: repos are injected per request,
    # but adapters on the registry use the container session factory indirectly
    # through services that construct request-scoped adapters.
    # Register request-agnostic bot/instagram adapters that receive repos at call
    # sites — SocialAccountService uses container.adapter_registry.get() which
    # needs fully wired adapters. Wire them with a shared session is wrong;
    # instead services rebuild adapters. Simpler approach: register adapters that
    # hold container ref and open sessions internally — but create_post already
    # gets account from service repo.

    # Practical approach: register adapters bound to session_factory via deferred repos.
    _register_adapters(container)
    return container


def _register_adapters(container: Container) -> None:
    """Register platform adapters. Repos are rebound per request in services.

    Bot/Instagram adapters need account_repo; we use a thin proxy that pulls
    session from contextvar OR we construct adapters inside services.
    Simplest fix: services call build_adapters(session) instead of container registry.

    For now, register adapters with None repos and patch in get_*_service.
    """
    from social_hub.infrastructure.db.repositories.social_account_repo import (
        SQLAlchemySocialAccountRepo,
    )
    from social_hub.infrastructure.db.repositories.social_aux_repos import (
        SQLAlchemyConnectSessionRepo,
        SQLAlchemyProviderCredentialRepo,
    )
    from social_hub.infrastructure.providers.zernio.key_resolver import ProviderKeyResolver

    # Use a dummy session-less registration replaced in deps — actually create
    # adapters that accept repos set on the container for the request.
    # Better: SocialAccountService builds adapters itself.

    class _LazyRegistry(PlatformAdapterRegistry):
        def __init__(self, outer: Container):
            super().__init__()
            self._outer = outer
            self._session = None

        def bind_session(self, session):
            self._session = session
            self._adapters.clear()
            settings = self._outer.settings
            encryptor = self._outer.encryptor
            account_repo = SQLAlchemySocialAccountRepo(session)
            connect_repo = SQLAlchemyConnectSessionRepo(session)
            key_resolver = ProviderKeyResolver(
                settings, encryptor, SQLAlchemyProviderCredentialRepo(session)
            )

            self.register(
                BotPlatformAdapter(
                    platform=PlatformType.TELEGRAM,
                    capabilities=SOCIAL_CAPABILITIES[PlatformType.TELEGRAM],
                    driver=TelegramDriver(),
                    account_repo=account_repo,
                    encryptor=encryptor,
                    settings=settings,
                )
            )
            self.register(
                BotPlatformAdapter(
                    platform=PlatformType.BALE,
                    capabilities=SOCIAL_CAPABILITIES[PlatformType.BALE],
                    driver=BaleDriver(),
                    account_repo=account_repo,
                    encryptor=encryptor,
                    settings=settings,
                )
            )
            self.register(
                BotPlatformAdapter(
                    platform=PlatformType.EITAA,
                    capabilities=SOCIAL_CAPABILITIES[PlatformType.EITAA],
                    driver=EitaaDriver(),
                    account_repo=account_repo,
                    encryptor=encryptor,
                    settings=settings,
                )
            )

            async def tenant_settings(tenant_id):
                from social_hub.infrastructure.db.repositories.tenant_repo import (
                    SQLAlchemyTenantRepo,
                )

                t = await SQLAlchemyTenantRepo(session).get_by_id(tenant_id)
                return t.settings if t else {}

            self.register(
                InstagramAdapter(
                    settings=settings,
                    key_resolver=key_resolver,
                    account_repo=account_repo,
                    connect_session_repo=connect_repo,
                    tenant_settings_provider=tenant_settings,
                )
            )

    lazy = _LazyRegistry(container)
    container.adapter_registry = lazy  # type: ignore


def _dev_key() -> str:
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()
