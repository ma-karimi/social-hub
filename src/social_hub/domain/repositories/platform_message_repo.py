from typing import Protocol
from uuid import UUID

from social_hub.domain.entities.platform_message import PlatformMessage


class PlatformMessageRepository(Protocol):
    async def create(self, message: PlatformMessage) -> PlatformMessage: ...
    async def list_by_publication(self, publication_id: UUID) -> list[PlatformMessage]: ...
