from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from social_hub.domain.value_objects.post_type import PostType


class PostStatus:
    DRAFT = "draft"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass
class PostContent:
    title: str
    body: str
    price: float | None = None
    currency: str | None = None
    images: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "body": self.body,
            "price": self.price,
            "currency": self.currency,
            "images": self.images,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PostContent":
        return cls(
            title=data.get("title", ""),
            body=data.get("body", ""),
            price=data.get("price"),
            currency=data.get("currency"),
            images=data.get("images", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Post:
    id: UUID
    tenant_id: UUID
    post_type: PostType
    content: PostContent
    status: str
    external_ref: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        post_type: PostType,
        content: PostContent,
        external_ref: str | None = None,
    ) -> "Post":
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            post_type=post_type,
            content=content,
            status=PostStatus.DRAFT,
            external_ref=external_ref,
        )
