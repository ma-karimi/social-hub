from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetPostStatusQuery:
    tenant_id: UUID
    post_id: UUID
