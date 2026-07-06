from uuid import UUID

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.exceptions import ConnectionNotFoundError
from social_hub.domain.repositories.connection_repo import ConnectionRepository
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor
from social_hub.shared.types import TenantContext


class ConnectionService:
    def __init__(
        self,
        connection_repo: ConnectionRepository,
        encryptor: FernetEncryptor,
    ) -> None:
        self._repo = connection_repo
        self._encryptor = encryptor

    async def create_connection(
        self,
        tenant_ctx: TenantContext,
        platform_type: PlatformType,
        credentials: dict,
        settings: dict | None = None,
    ) -> PlatformConnection:
        encrypted = self._encryptor.encrypt(credentials)
        connection = PlatformConnection.create(
            tenant_id=tenant_ctx.tenant_id,
            platform_type=platform_type,
            credentials_encrypted=encrypted,
            settings=settings or {},
        )
        return await self._repo.create(connection)

    async def get_connection(
        self, tenant_ctx: TenantContext, connection_id: UUID
    ) -> PlatformConnection:
        conn = await self._repo.get_by_id(tenant_ctx.tenant_id, connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        return conn

    async def list_connections(self, tenant_ctx: TenantContext) -> list[PlatformConnection]:
        return await self._repo.list_by_tenant(tenant_ctx.tenant_id)

    async def update_connection(
        self,
        tenant_ctx: TenantContext,
        connection_id: UUID,
        credentials: dict | None = None,
        settings: dict | None = None,
        is_active: bool | None = None,
    ) -> PlatformConnection:
        conn = await self.get_connection(tenant_ctx, connection_id)
        if credentials is not None:
            conn.credentials_encrypted = self._encryptor.encrypt(credentials)
        if settings is not None:
            conn.settings = {**conn.settings, **settings}
        if is_active is not None:
            conn.is_active = is_active
        return await self._repo.update(conn)

    async def delete_connection(
        self, tenant_ctx: TenantContext, connection_id: UUID
    ) -> None:
        await self.get_connection(tenant_ctx, connection_id)
        await self._repo.delete(tenant_ctx.tenant_id, connection_id)

    def decrypt_credentials(self, connection: PlatformConnection) -> dict:
        return self._encryptor.decrypt(connection.credentials_encrypted)
