from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.tenant import Tenant
from social_hub.infrastructure.db.models.tenant import TenantModel


def _to_entity(m: TenantModel) -> Tenant:
    return Tenant(
        id=m.id,
        name=m.name,
        api_key_hash=m.api_key_hash,
        is_active=m.is_active,
        settings=m.settings or {},
        created_at=m.created_at,
    )


class SQLAlchemyTenantRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant: Tenant) -> Tenant:
        model = TenantModel(
            id=tenant.id,
            name=tenant.name,
            api_key_hash=tenant.api_key_hash,
            is_active=tenant.is_active,
            settings=tenant.settings,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        result = await self._session.get(TenantModel, tenant_id)
        return _to_entity(result) if result else None

    async def get_by_api_key_hash(self, api_key_hash: str) -> Tenant | None:
        stmt = select(TenantModel).where(TenantModel.api_key_hash == api_key_hash)
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None

    async def update(self, tenant: Tenant) -> Tenant:
        model = await self._session.get(TenantModel, tenant.id)
        if model is None:
            raise ValueError(f"Tenant {tenant.id} not found")
        model.name = tenant.name
        model.api_key_hash = tenant.api_key_hash
        model.is_active = tenant.is_active
        model.settings = tenant.settings
        await self._session.flush()
        return _to_entity(model)

    async def list_all(self) -> list[Tenant]:
        result = await self._session.scalars(select(TenantModel))
        return [_to_entity(m) for m in result]
