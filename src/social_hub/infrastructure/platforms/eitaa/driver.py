import structlog

from social_hub.domain.value_objects.capabilities import PlatformCapabilities
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.base import (
    ConnectionContext,
    DeleteResult,
    EditResult,
    PlatformDriver,
    PublishResult,
)
from social_hub.infrastructure.platforms.capabilities import PLATFORM_CAPABILITIES
from social_hub.infrastructure.platforms.dto.incoming_event import IncomingEvent
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost
from social_hub.infrastructure.platforms.eitaa.client import EitaaAPIError, EitaaClient

logger = structlog.get_logger(__name__)


class EitaaDriver(PlatformDriver):
    """
    Eitaayar channel publisher.

    The public Eitaayar API supports getMe / sendMessage / sendFile only —
    no edit, delete, buttons, or inbound webhooks.
    """

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.EITAA

    @property
    def capabilities(self) -> PlatformCapabilities:
        return PLATFORM_CAPABILITIES[PlatformType.EITAA]

    def _client(self, ctx: ConnectionContext) -> EitaaClient:
        return EitaaClient(ctx.credentials["bot_token"])

    def _channel_id(self, ctx: ConnectionContext) -> str:
        return str(ctx.connection.settings["channel_id"])

    def _publish_options(self, ctx: ConnectionContext) -> dict:
        settings = ctx.connection.settings
        options: dict = {
            "title": settings.get("title"),
            "pin": bool(settings.get("pin", False)),
            "disable_notification": bool(settings.get("disable_notification", False)),
        }
        if settings.get("view_count_for_delete") is not None:
            options["view_count_for_delete"] = int(settings["view_count_for_delete"])
        return options

    async def publish(self, ctx: ConnectionContext, outgoing: OutgoingPost) -> PublishResult:
        client = self._client(ctx)
        channel_id = self._channel_id(ctx)
        options = self._publish_options(ctx)

        try:
            if not outgoing.media:
                result = await client.send_message(
                    chat_id=channel_id,
                    text=outgoing.text,
                    **options,
                )
            else:
                # Eitaayar has no media albums — publish the first attachment only.
                result = await client.send_file_from_url(
                    chat_id=channel_id,
                    url=outgoing.media[0].url,
                    caption=outgoing.text,
                    **options,
                )

            message_id = result.get("message_id")
            chat = result.get("chat") or {}
            chat_id = chat.get("id", channel_id)
            return PublishResult(
                success=True,
                platform_message_id=str(message_id) if message_id is not None else None,
                chat_id=str(chat_id),
            )
        except EitaaAPIError as exc:
            logger.error("eitaa_publish_failed", error=exc.description, code=exc.error_code)
            return PublishResult(success=False, error_message=exc.description)
        except Exception as exc:
            logger.exception("eitaa_publish_unexpected", error=str(exc))
            return PublishResult(success=False, error_message=str(exc))

    async def edit(
        self,
        ctx: ConnectionContext,
        platform_message_id: str,
        chat_id: str,
        outgoing: OutgoingPost,
    ) -> EditResult:
        return EditResult(
            success=False,
            error_message="Eitaa (Eitaayar) API does not support editing messages",
        )

    async def delete(
        self,
        ctx: ConnectionContext,
        platform_message_id: str,
        chat_id: str,
    ) -> DeleteResult:
        return DeleteResult(
            success=False,
            error_message="Eitaa (Eitaayar) API does not support deleting messages",
        )

    def parse_incoming(self, raw: dict) -> IncomingEvent | None:
        # Eitaayar has no inbound webhook updates.
        return None

    def verify_webhook(self, headers: dict, body: bytes, secret: str | None = None) -> bool:
        # No webhook surface — accept only when no secret is configured.
        return secret is None
