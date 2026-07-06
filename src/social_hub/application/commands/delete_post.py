from dataclasses import dataclass
from uuid import UUID


@dataclass
class DeletePostCommand:
    tenant_id: UUID
    post_id: UUID
