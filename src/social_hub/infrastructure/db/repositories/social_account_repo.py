from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.social_account import SocialAccount
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.models.social_account import SocialAccountModel


def _to_entity(m: SocialAccountModel) -> SocialAccount:
    return SocialAccount(
        id=m.id,
        tenant_id=m.tenant_id,
        platform=PlatformType(m.platform),
        external_account_id=m.external_account_id,
        credentials_encrypted=bytes(m.credentials_encrypted) if m.credentials_encrypted else None,
        login_method=m.login_method,
        display_name=m.display_name,
        username=m.username,
        settings=m.settings or {},
        metadata=m.account_metadata or {},
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemySocialAccountRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, account: SocialAccount) -> SocialAccount:
        model = SocialAccountModel(
            id=account.id,
            tenant_id=account.tenant_id,
            platform=account.platform.value,
            external_account_id=account.external_account_id,
            login_method=account.login_method,
            display_name=account.display_name,
            username=account.username,
            credentials_encrypted=account.credentials_encrypted,
            settings=account.settings,
            account_metadata=account.metadata,
            is_active=account.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, tenant_id: UUID, account_id: UUID) -> SocialAccount | None:
        stmt = select(SocialAccountModel).where(
            SocialAccountModel.id == account_id,
            SocialAccountModel.tenant_id == tenant_id,
        )
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None

    async def get_by_id_unscoped(self, account_id: UUID) -> SocialAccount | None:
        result = await self._session.get(SocialAccountModel, account_id)
        return _to_entity(result) if result else None

    async def list_by_tenant(
        self, tenant_id: UUID, platform: PlatformType | None = None
    ) -> list[SocialAccount]:
        stmt = select(SocialAccountModel).where(SocialAccountModel.tenant_id == tenant_id)
        if platform is not None:
            stmt = stmt.where(SocialAccountModel.platform == platform.value)
        results = await self._session.scalars(stmt)
        return [_to_entity(m) for m in results]

    async def update(self, account: SocialAccount) -> SocialAccount:
        model = await self._session.get(SocialAccountModel, account.id)
        if model is None:
            raise ValueError(f"Social account {account.id} not found")
        model.credentials_encrypted = account.credentials_encrypted
        model.settings = account.settings
        model.account_metadata = account.metadata
        model.is_active = account.is_active
        model.display_name = account.display_name
        model.username = account.username
        model.login_method = account.login_method
        model.external_account_id = account.external_account_id
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, tenant_id: UUID, account_id: UUID) -> None:
        stmt = delete(SocialAccountModel).where(
            SocialAccountModel.id == account_id,
            SocialAccountModel.tenant_id == tenant_id,
        )
        await self._session.execute(stmt)
