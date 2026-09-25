import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from social_hub.infrastructure.db.models.base import Base


class SocialAccountModel(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "platform", "external_account_id", name="uq_tenant_platform_external"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    login_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credentials_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    account_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantProviderCredentialModel(Base):
    __tablename__ = "tenant_provider_credentials"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_tenant_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    profile_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ConnectSessionModel(Base):
    __tablename__ = "connect_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    our_connect_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    upstream_connect_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    consumer_redirect_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    login_method: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MediaRelayKeyModel(Base):
    """Maps opaque public relay keys to upstream CDN paths (no file storage)."""

    __tablename__ = "media_relay_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opaque_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    upstream_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    upstream_public_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
