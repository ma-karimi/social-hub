from typing import Protocol
from uuid import UUID

from social_hub.domain.entities.interaction_event import InteractionEvent


class InteractionEventRepository(Protocol):
    async def create(self, event: InteractionEvent) -> InteractionEvent: ...
    async def get_by_id(self, event_id: UUID) -> InteractionEvent | None: ...
    async def update(self, event: InteractionEvent) -> InteractionEvent: ...
