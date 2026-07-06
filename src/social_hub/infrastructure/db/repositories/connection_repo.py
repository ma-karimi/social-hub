from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.models.platform_connection import PlatformConnectionModel


def _to_entity(m: PlatformConnectionModel) -> PlatformConnection:
    return PlatformConnection(
        id=m.id,
        tenant_id=m.tenant_id,
        platform_type=PlatformType(m.platform_type),
        credentials_encrypted=bytes(m.credentials_encrypted),
        settings=m.settings or {},
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyConnectionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, connection: PlatformConnection) -> PlatformConnection:
        model = PlatformConnectionModel(
            id=connection.id,
            tenant_id=connection.tenant_id,
            platform_type=connection.platform_type,
            credentials_encrypted=connection.credentials_encrypted,
            settings=connection.settings,
            is_active=connection.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, tenant_id: UUID, connection_id: UUID) -> PlatformConnection | None:
        stmt = select(PlatformConnectionModel).where(
            PlatformConnectionModel.id == connection_id,
            PlatformConnectionModel.tenant_id == tenant_id,
        )
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None

    async def get_by_platform(
        self, tenant_id: UUID, platform_type: PlatformType
    ) -> PlatformConnection | None:
        stmt = select(PlatformConnectionModel).where(
            PlatformConnectionModel.tenant_id == tenant_id,
            PlatformConnectionModel.platform_type == platform_type,
        )
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None

    async def list_by_tenant(self, tenant_id: UUID) -> list[PlatformConnection]:
        stmt = select(PlatformConnectionModel).where(
            PlatformConnectionModel.tenant_id == tenant_id
        )
        results = await self._session.scalars(stmt)
        return [_to_entity(m) for m in results]

    async def update(self, connection: PlatformConnection) -> PlatformConnection:
        model = await self._session.get(PlatformConnectionModel, connection.id)
        if model is None:
            raise ValueError(f"Connection {connection.id} not found")
        model.credentials_encrypted = connection.credentials_encrypted
        model.settings = connection.settings
        model.is_active = connection.is_active
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, tenant_id: UUID, connection_id: UUID) -> None:
        stmt = delete(PlatformConnectionModel).where(
            PlatformConnectionModel.id == connection_id,
            PlatformConnectionModel.tenant_id == tenant_id,
        )
        await self._session.execute(stmt)
