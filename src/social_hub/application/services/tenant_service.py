from uuid import UUID

from social_hub.domain.entities.tenant import Tenant
from social_hub.domain.exceptions import TenantNotFoundError
from social_hub.domain.repositories.tenant_repo import TenantRepository
from social_hub.shared.utils import generate_api_key, hash_api_key


class TenantService:
    def __init__(self, tenant_repo: TenantRepository) -> None:
        self._repo = tenant_repo

    async def create_tenant(self, name: str, settings: dict | None = None) -> tuple[Tenant, str]:
        """Create a tenant. Returns (tenant, plain_api_key) — store the key securely."""
        api_key = generate_api_key()
        tenant = Tenant.create(
            name=name,
            api_key_hash=hash_api_key(api_key),
            settings=settings or {},
        )
        tenant = await self._repo.create(tenant)
        return tenant, api_key

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        return tenant

    async def list_tenants(self) -> list[Tenant]:
        return await self._repo.list_all()

    async def update_settings(self, tenant_id: UUID, settings: dict) -> Tenant:
        tenant = await self.get_tenant(tenant_id)
        tenant.settings = {**tenant.settings, **settings}
        return await self._repo.update(tenant)

    async def regenerate_api_key(self, tenant_id: UUID) -> tuple[Tenant, str]:
        """Regenerate API key. Returns (tenant, new_plain_api_key)."""
        tenant = await self.get_tenant(tenant_id)
        api_key = generate_api_key()
        tenant.api_key_hash = hash_api_key(api_key)
        tenant = await self._repo.update(tenant)
        return tenant, api_key

    async def resolve_from_api_key(self, api_key: str) -> Tenant | None:
        """Look up a tenant from a plain API key. Returns None if not found."""
        return await self._repo.get_by_api_key_hash(hash_api_key(api_key))
