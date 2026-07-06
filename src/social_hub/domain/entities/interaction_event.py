from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.button_action import ButtonAction


class InteractionStatus:
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class ReplyContext:
    """Context needed to send a reply in the originating platform."""
    chat_id: str
    message_id: str | None = None
    callback_query_id: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class InteractionEvent:
    id: UUID
    tenant_id: UUID
    platform_type: PlatformType
    user_platform_id: str
    raw_payload: dict
    button_id: UUID | None = None
    action: ButtonAction | None = None
    payload: dict = field(default_factory=dict)
    reply_context: ReplyContext | None = None
    status: str = InteractionStatus.PENDING
    processed_at: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        platform_type: PlatformType,
        user_platform_id: str,
        raw_payload: dict,
        button_id: UUID | None = None,
        action: ButtonAction | None = None,
        payload: dict | None = None,
        reply_context: ReplyContext | None = None,
    ) -> "InteractionEvent":
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            platform_type=platform_type,
            user_platform_id=user_platform_id,
            raw_payload=raw_payload,
            button_id=button_id,
            action=action,
            payload=payload or {},
            reply_context=reply_context,
        )
