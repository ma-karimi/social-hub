from dataclasses import dataclass
from uuid import UUID
from typing import NewType

TenantId = NewType("TenantId", UUID)
PostId = NewType("PostId", UUID)
PublicationId = NewType("PublicationId", UUID)
ButtonId = NewType("ButtonId", UUID)
ConnectionId = NewType("ConnectionId", UUID)


@dataclass(frozen=True)
class TenantContext:
    """Resolved tenant identity, injected from API Key middleware."""
    tenant_id: UUID
    tenant_name: str
