"""Composition root — wires all singletons together."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from social_hub.application.services.capability_resolver import CapabilityResolver
from social_hub.config import Settings
from social_hub.infrastructure.db.session import create_session_factory
from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor
from social_hub.infrastructure.platforms.registry import DriverRegistry
from social_hub.infrastructure.platforms.telegram.driver import TelegramDriver


@dataclass
class Container:
    session_factory: async_sessionmaker[AsyncSession]
    encryptor: FernetEncryptor
    driver_registry: DriverRegistry
    capability_resolver: CapabilityResolver
    arq_redis: object  # arq.ArqRedis — typed loosely to avoid hard import at definition time


async def build_container(settings: Settings) -> Container:
    from arq import create_pool
    from arq.connections import RedisSettings

    session_factory = create_session_factory(settings.database_url)

    encryptor = FernetEncryptor(settings.encryption_key or _dev_key())

    driver_registry = DriverRegistry()
    driver_registry.register(TelegramDriver())

    capability_resolver = CapabilityResolver()

    arq_redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    return Container(
        session_factory=session_factory,
        encryptor=encryptor,
        driver_registry=driver_registry,
        capability_resolver=capability_resolver,
        arq_redis=arq_redis,
    )


def _dev_key() -> str:
    """Fallback Fernet key for development only (not for production)."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()
