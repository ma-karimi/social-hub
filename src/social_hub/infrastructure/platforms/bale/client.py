import httpx
import structlog

logger = structlog.get_logger(__name__)

BALE_API_BASE = "https://tapi.bale.ai/bot{token}"


class BaleAPIError(Exception):
    def __init__(self, description: str, error_code: int | None = None) -> None:
        self.description = description
        self.error_code = error_code
        super().__init__(f"Bale API error {error_code}: {description}")


class BaleClient:
    """HTTP client for Bale Bot API (Telegram-compatible surface at tapi.bale.ai)."""

    def __init__(self, bot_token: str) -> None:
        self._base = f"https://tapi.bale.ai/bot{bot_token}"

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict:
        payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._post("sendMessage", payload)

    async def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: str | None = None,
        reply_markup: dict | None = None,
    ) -> dict:
        payload: dict = {"chat_id": chat_id, "photo": photo}
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._post("sendPhoto", payload)

    async def edit_message_text(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict:
        payload: dict = {
            "chat_id": chat_id,
            "message_id": int(message_id),
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._post("editMessageText", payload)

    async def edit_message_caption(
        self,
        chat_id: str,
        message_id: str,
        caption: str,
        reply_markup: dict | None = None,
    ) -> dict:
        payload: dict = {
            "chat_id": chat_id,
            "message_id": int(message_id),
            "caption": caption,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._post("editMessageCaption", payload)

    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        await self._post("deleteMessage", {"chat_id": chat_id, "message_id": int(message_id)})
        return True

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
    ) -> bool:
        payload: dict = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        await self._post("answerCallbackQuery", payload)
        return True

    async def set_webhook(self, url: str) -> bool:
        await self._post("setWebhook", {"url": url})
        return True

    async def get_me(self) -> dict:
        return await self._post("getMe", {})

    async def _post(self, method: str, payload: dict) -> dict | list:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self._base}/{method}", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                error_code = data.get("error_code")
                description = data.get("description", "Unknown error")
                logger.warning("bale_api_error", method=method, code=error_code, desc=description)
                raise BaleAPIError(description, error_code)
            return data["result"]
