from dataclasses import dataclass
from uuid import UUID

from social_hub.domain.entities.post import PostContent


@dataclass
class EditPostCommand:
    tenant_id: UUID
    post_id: UUID
    new_content: PostContent
