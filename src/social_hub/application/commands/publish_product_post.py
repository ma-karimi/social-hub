from dataclasses import dataclass, field
from uuid import UUID

from social_hub.domain.entities.post import PostContent
from social_hub.domain.value_objects.platform_type import PlatformType


@dataclass
class PublishProductPostCommand:
    tenant_id: UUID
    platforms: list[PlatformType]
    content: PostContent
    buttons_data: list[dict] = field(default_factory=list)
    external_ref: str | None = None
