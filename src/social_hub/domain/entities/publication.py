from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from social_hub.domain.value_objects.publication_status import PublicationStatus


@dataclass
class Publication:
    id: UUID
    post_id: UUID
    account_id: UUID
    status: PublicationStatus
    error_message: str | None = None
    platform_metadata: dict = field(default_factory=dict)
    published_at: datetime | None = None
    created_at: datetime | None = None

    # Back-compat alias used by older call sites during migration
    @property
    def connection_id(self) -> UUID:
        return self.account_id

    @classmethod
    def create(cls, post_id: UUID, account_id: UUID) -> "Publication":
        return cls(
            id=uuid4(),
            post_id=post_id,
            account_id=account_id,
            status=PublicationStatus.PENDING,
        )
