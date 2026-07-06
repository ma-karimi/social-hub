from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    event_id: UUID
    occurred_at: datetime

    @classmethod
    def new(cls, **kwargs) -> "DomainEvent":
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            **kwargs,
        )
