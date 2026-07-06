from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from social_hub.domain.value_objects.platform_type import PlatformType


@dataclass
class PlatformConnection:
    id: UUID
    tenant_id: UUID
    platform_type: PlatformType
    credentials_encrypted: bytes
    settings: dict = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        platform_type: PlatformType,
        credentials_encrypted: bytes,
        settings: dict | None = None,
    ) -> "PlatformConnection":
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            platform_type=platform_type,
            credentials_encrypted=credentials_encrypted,
            settings=settings or {},
        )
