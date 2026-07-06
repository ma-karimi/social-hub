from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class PlatformMessage:
    """Maps a Publication to the actual message ID on the platform (for edit/delete)."""
    id: UUID
    publication_id: UUID
    platform_message_id: str
    chat_id: str

    @classmethod
    def create(
        cls,
        publication_id: UUID,
        platform_message_id: str,
        chat_id: str,
    ) -> "PlatformMessage":
        return cls(
            id=uuid4(),
            publication_id=publication_id,
            platform_message_id=platform_message_id,
            chat_id=chat_id,
        )
