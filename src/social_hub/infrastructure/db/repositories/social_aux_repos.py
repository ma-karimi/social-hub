from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.connect_session import ConnectSession
from social_hub.infrastructure.db.models.social_account import (
    ConnectSessionModel,
    MediaRelayKeyModel,
    TenantProviderCredentialModel,
)


class SQLAlchemyConnectSessionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session: ConnectSession) -> ConnectSession:
        model = ConnectSessionModel(
            id=session.id,
            our_connect_token=session.our_connect_token,
            upstream_connect_token=session.upstream_connect_token,
            tenant_id=session.tenant_id,
            platform=session.platform,
            consumer_redirect_url=session.consumer_redirect_url,
            login_method=session.login_method,
            mode=session.mode,
            expires_at=session.expires_at,
            session_metadata=session.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        return session

    async def get_by_token(self, token: str) -> ConnectSession | None:
        stmt = select(ConnectSessionModel).where(ConnectSessionModel.our_connect_token == token)
        m = await self._session.scalar(stmt)
        if m is None:
            return None
        return ConnectSession(
            id=m.id,
            our_connect_token=m.our_connect_token,
            upstream_connect_token=m.upstream_connect_token,
            tenant_id=m.tenant_id,
            platform=m.platform,
            consumer_redirect_url=m.consumer_redirect_url,
            login_method=m.login_method,
            mode=m.mode,
            expires_at=m.expires_at,
            metadata=m.session_metadata or {},
            created_at=m.created_at,
        )

    async def update(self, session: ConnectSession) -> ConnectSession:
        model = await self._session.get(ConnectSessionModel, session.id)
        if model is None:
            raise ValueError("Connect session not found")
        model.upstream_connect_token = session.upstream_connect_token
        model.session_metadata = session.metadata
        await self._session.flush()
        return session

    async def delete(self, session_id: UUID) -> None:
        await self._session.execute(
            delete(ConnectSessionModel).where(ConnectSessionModel.id == session_id)
        )


class SQLAlchemyProviderCredentialRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: UUID, provider: str = "zernio") -> TenantProviderCredentialModel | None:
        stmt = select(TenantProviderCredentialModel).where(
            TenantProviderCredentialModel.tenant_id == tenant_id,
            TenantProviderCredentialModel.provider == provider,
        )
        return await self._session.scalar(stmt)

    async def upsert(
        self,
        tenant_id: UUID,
        api_key_encrypted: bytes,
        profile_id: str | None = None,
        provider: str = "zernio",
    ) -> TenantProviderCredentialModel:
        existing = await self.get(tenant_id, provider)
        if existing:
            existing.api_key_encrypted = api_key_encrypted
            if profile_id is not None:
                existing.profile_id = profile_id
            await self._session.flush()
            return existing
        from uuid import uuid4

        model = TenantProviderCredentialModel(
            id=uuid4(),
            tenant_id=tenant_id,
            provider=provider,
            api_key_encrypted=api_key_encrypted,
            profile_id=profile_id,
        )
        self._session.add(model)
        await self._session.flush()
        return model


class SQLAlchemyMediaRelayRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        opaque_key: str,
        upstream_path: str,
        upstream_public_url: str,
        tenant_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> MediaRelayKeyModel:
        from uuid import uuid4

        model = MediaRelayKeyModel(
            id=uuid4(),
            opaque_key=opaque_key,
            upstream_path=upstream_path,
            upstream_public_url=upstream_public_url,
            tenant_id=tenant_id,
            expires_at=expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_opaque_key(self, opaque_key: str) -> MediaRelayKeyModel | None:
        stmt = select(MediaRelayKeyModel).where(MediaRelayKeyModel.opaque_key == opaque_key)
        return await self._session.scalar(stmt)
