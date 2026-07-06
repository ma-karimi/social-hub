import hmac
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
from social_hub.infrastructure.platforms.telegram.button_encoder import build_inline_keyboard
from social_hub.infrastructure.platforms.telegram.client import TelegramAPIError, TelegramClient
from social_hub.infrastructure.platforms.telegram.webhook_parser import parse_update

logger = structlog.get_logger(__name__)


class TelegramDriver(PlatformDriver):
    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.TELEGRAM

    @property
    def capabilities(self) -> PlatformCapabilities:
        return PLATFORM_CAPABILITIES[PlatformType.TELEGRAM]

    def _client(self, ctx: ConnectionContext) -> TelegramClient:
        return TelegramClient(ctx.credentials["bot_token"])

    def _channel_id(self, ctx: ConnectionContext) -> str:
        return ctx.connection.settings["channel_id"]

    async def publish(self, ctx: ConnectionContext, outgoing: OutgoingPost) -> PublishResult:
        client = self._client(ctx)
        channel_id = self._channel_id(ctx)
        reply_markup = build_inline_keyboard(outgoing.buttons) if outgoing.buttons else None

        try:
            if len(outgoing.media) == 0:
                result = await client.send_message(
                    chat_id=channel_id,
                    text=outgoing.text,
                    reply_markup=reply_markup,
                )
                return PublishResult(
                    success=True,
                    platform_message_id=str(result["message_id"]),
                    chat_id=str(result["chat"]["id"]),
                )

            if len(outgoing.media) == 1:
                result = await client.send_photo(
                    chat_id=channel_id,
                    photo=outgoing.media[0].url,
                    caption=outgoing.text,
                    reply_markup=reply_markup,
                )
                return PublishResult(
                    success=True,
                    platform_message_id=str(result["message_id"]),
                    chat_id=str(result["chat"]["id"]),
                )

            # Multiple images: send as media group (no buttons support in media group)
            media_items = []
            for i, ref in enumerate(outgoing.media):
                item: dict = {"type": "photo", "media": ref.url}
                if i == 0:
                    item["caption"] = outgoing.text
                    item["parse_mode"] = "HTML"
                media_items.append(item)

            results = await client.send_media_group(chat_id=channel_id, media=media_items)
            first = results[0] if isinstance(results, list) else results  # type: ignore[index]
            return PublishResult(
                success=True,
                platform_message_id=str(first["message_id"]),
                chat_id=str(first["chat"]["id"]),
            )

        except TelegramAPIError as exc:
            logger.error("telegram_publish_failed", error=exc.description, code=exc.error_code)
            return PublishResult(success=False, error_message=exc.description)
        except Exception as exc:
            logger.exception("telegram_publish_unexpected", error=str(exc))
            return PublishResult(success=False, error_message=str(exc))

    async def edit(
        self,
        ctx: ConnectionContext,
        platform_message_id: str,
        chat_id: str,
        outgoing: OutgoingPost,
    ) -> EditResult:
        client = self._client(ctx)
        reply_markup = build_inline_keyboard(outgoing.buttons) if outgoing.buttons else None

        try:
            if outgoing.media:
                await client.edit_message_caption(
                    chat_id=chat_id,
                    message_id=platform_message_id,
                    caption=outgoing.text,
                    reply_markup=reply_markup,
                )
            else:
                await client.edit_message_text(
                    chat_id=chat_id,
                    message_id=platform_message_id,
                    text=outgoing.text,
                    reply_markup=reply_markup,
                )
            return EditResult(success=True)
        except TelegramAPIError as exc:
            logger.error("telegram_edit_failed", error=exc.description, code=exc.error_code)
            return EditResult(success=False, error_message=exc.description)
        except Exception as exc:
            logger.exception("telegram_edit_unexpected", error=str(exc))
            return EditResult(success=False, error_message=str(exc))

    async def delete(
        self,
        ctx: ConnectionContext,
        platform_message_id: str,
        chat_id: str,
    ) -> DeleteResult:
        client = self._client(ctx)
        try:
            await client.delete_message(chat_id=chat_id, message_id=platform_message_id)
            return DeleteResult(success=True)
        except TelegramAPIError as exc:
            logger.error("telegram_delete_failed", error=exc.description, code=exc.error_code)
            return DeleteResult(success=False, error_message=exc.description)
        except Exception as exc:
            logger.exception("telegram_delete_unexpected", error=str(exc))
            return DeleteResult(success=False, error_message=str(exc))

    def parse_incoming(self, raw: dict) -> IncomingEvent | None:
        return parse_update(raw)

    def verify_webhook(self, headers: dict, body: bytes, secret: str | None = None) -> bool:
        if not secret:
            return True
        token = headers.get("x-telegram-bot-api-secret-token") or headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )
        if token is None:
            return False
        return hmac.compare_digest(token, secret)

    async def reply_to_interaction(
        self,
        ctx: ConnectionContext,
        chat_id: str,
        text: str,
        callback_query_id: str | None = None,
    ) -> None:
        client = self._client(ctx)
        if callback_query_id:
            await client.answer_callback_query(callback_query_id, text=text[:200])
        else:
            await client.send_message(chat_id=chat_id, text=text)
