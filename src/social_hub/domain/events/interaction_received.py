from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

from social_hub.domain.events.domain_event import DomainEvent
from social_hub.domain.value_objects.platform_type import PlatformType


@dataclass
class InteractionReceived(DomainEvent):
    tenant_id: UUID
    interaction_event_id: UUID
    platform_type: PlatformType
