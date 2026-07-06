from abc import ABC, abstractmethod
from dataclasses import dataclass

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.capabilities import PlatformCapabilities
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.dto.incoming_event import IncomingEvent
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost


@dataclass
class PublishResult:
    success: bool
    platform_message_id: str | None = None
    chat_id: str | None = None
    error_message: str | None = None


@dataclass
class EditResult:
    success: bool
    error_message: str | None = None


@dataclass
class DeleteResult:
    success: bool
    error_message: str | None = None


@dataclass
class ConnectionContext:
    """Bundles a connection with its decrypted credentials for use by drivers."""
    connection: PlatformConnection
    credentials: dict


class PlatformDriver(ABC):
    @property
    @abstractmethod
    def platform_type(self) -> PlatformType: ...

    @property
    @abstractmethod
    def capabilities(self) -> PlatformCapabilities: ...

    @abstractmethod
    async def publish(self, ctx: ConnectionContext, outgoing: OutgoingPost) -> PublishResult: ...

    @abstractmethod
    async def edit(
        self,
        ctx: ConnectionContext,
        platform_message_id: str,
        chat_id: str,
        outgoing: OutgoingPost,
    ) -> EditResult: ...

    @abstractmethod
    async def delete(
        self,
        ctx: ConnectionContext,
        platform_message_id: str,
        chat_id: str,
    ) -> DeleteResult: ...

    @abstractmethod
    def parse_incoming(self, raw: dict) -> IncomingEvent | None: ...

    @abstractmethod
    def verify_webhook(self, headers: dict, body: bytes, secret: str | None = None) -> bool: ...

    async def reply_to_interaction(
        self,
        ctx: ConnectionContext,
        chat_id: str,
        text: str,
        callback_query_id: str | None = None,
    ) -> None:
        """Send a reply in the platform. Default no-op for API-only platforms."""
