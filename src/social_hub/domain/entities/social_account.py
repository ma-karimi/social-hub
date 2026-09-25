from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from social_hub.domain.value_objects.platform_type import PlatformType


@dataclass
class SocialAccount:
    id: UUID
    tenant_id: UUID
    platform: PlatformType
    external_account_id: str
    credentials_encrypted: bytes | None = None
    login_method: str | None = None
    display_name: str | None = None
    username: str | None = None
    settings: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        platform: PlatformType,
        external_account_id: str,
        *,
        credentials_encrypted: bytes | None = None,
        login_method: str | None = None,
        display_name: str | None = None,
        username: str | None = None,
        settings: dict | None = None,
        metadata: dict | None = None,
    ) -> "SocialAccount":
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            platform=platform,
            external_account_id=external_account_id,
            credentials_encrypted=credentials_encrypted,
            login_method=login_method,
            display_name=display_name,
            username=username,
            settings=settings or {},
            metadata=metadata or {},
        )
