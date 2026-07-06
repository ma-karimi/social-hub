from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from social_hub.domain.value_objects.publication_status import PublicationStatus


@dataclass
class Publication:
    id: UUID
    post_id: UUID
    connection_id: UUID
    status: PublicationStatus
    error_message: str | None = None
    platform_metadata: dict = field(default_factory=dict)
    published_at: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def create(cls, post_id: UUID, connection_id: UUID) -> "Publication":
        return cls(
            id=uuid4(),
            post_id=post_id,
            connection_id=connection_id,
            status=PublicationStatus.PENDING,
        )
