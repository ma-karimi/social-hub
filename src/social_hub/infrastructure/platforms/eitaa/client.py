from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse

import httpx
import structlog

logger = structlog.get_logger(__name__)

EITAA_API_BASE = "https://eitaayar.ir/api/{token}"


class EitaaAPIError(Exception):
    def __init__(self, description: str, error_code: int | None = None) -> None:
        self.description = description
        self.error_code = error_code
        super().__init__(f"Eitaa API error {error_code}: {description}")


class EitaaClient:
    """HTTP client for Eitaayar API (https://eitaayar.ir/api/{token}/{method})."""

    def __init__(self, bot_token: str) -> None:
        self._base = f"https://eitaayar.ir/api/{bot_token}"

    async def get_me(self) -> dict:
        return await self._request("getMe")

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        title: str | None = None,
        pin: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        date: int | None = None,
        view_count_for_delete: int | None = None,
    ) -> dict:
        payload: dict = {
            "chat_id": self._normalize_chat_id(chat_id),
            "text": text,
        }
        self._apply_common_options(
            payload,
            title=title,
            pin=pin,
            disable_notification=disable_notification,
            reply_to_message_id=reply_to_message_id,
            date=date,
            view_count_for_delete=view_count_for_delete,
        )
        return await self._request("sendMessage", data=payload)

    async def send_file(
        self,
        chat_id: str,
        file: bytes | BinaryIO,
        filename: str,
        caption: str | None = None,
        *,
        title: str | None = None,
        pin: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        date: int | None = None,
        view_count_for_delete: int | None = None,
    ) -> dict:
        data: dict = {"chat_id": self._normalize_chat_id(chat_id)}
        if caption:
            data["caption"] = caption
        self._apply_common_options(
            data,
            title=title,
            pin=pin,
            disable_notification=disable_notification,
            reply_to_message_id=reply_to_message_id,
            date=date,
            view_count_for_delete=view_count_for_delete,
        )
        files = {"file": (filename, file)}
        return await self._request("sendFile", data=data, files=files)

    async def send_file_from_url(
        self,
        chat_id: str,
        url: str,
        caption: str | None = None,
        *,
        title: str | None = None,
        pin: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        date: int | None = None,
        view_count_for_delete: int | None = None,
    ) -> dict:
        """Download a remote file and upload it via sendFile."""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.content
            filename = self._filename_from_url(url, resp.headers.get("content-type"))

        return await self.send_file(
            chat_id=chat_id,
            file=content,
            filename=filename,
            caption=caption,
            title=title,
            pin=pin,
            disable_notification=disable_notification,
            reply_to_message_id=reply_to_message_id,
            date=date,
            view_count_for_delete=view_count_for_delete,
        )

    @staticmethod
    def _normalize_chat_id(chat_id: str) -> str:
        # Eitaayar expects channel username without leading '@'.
        return chat_id[1:] if chat_id.startswith("@") else chat_id

    @staticmethod
    def _filename_from_url(url: str, content_type: str | None) -> str:
        path = Path(urlparse(url).path)
        if path.name and "." in path.name:
            return path.name
        ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "application/pdf": ".pdf",
        }.get((content_type or "").split(";")[0].strip(), ".bin")
        return f"file{ext}"

    @staticmethod
    def _apply_common_options(
        payload: dict,
        *,
        title: str | None,
        pin: bool,
        disable_notification: bool,
        reply_to_message_id: int | None,
        date: int | None,
        view_count_for_delete: int | None,
    ) -> None:
        if title:
            payload["title"] = title
        if pin:
            payload["pin"] = 1
        if disable_notification:
            payload["disable_notification"] = 1
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if date is not None:
            payload["date"] = date
        if view_count_for_delete is not None:
            payload["viewCountForDelete"] = view_count_for_delete

    async def _request(
        self,
        method: str,
        data: dict | None = None,
        files: dict | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if files:
                resp = await client.post(f"{self._base}/{method}", data=data or {}, files=files)
            elif data is not None:
                resp = await client.post(f"{self._base}/{method}", json=data)
            else:
                resp = await client.post(f"{self._base}/{method}")

            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("ok"):
                description = payload.get("description") or payload.get("error") or "Unknown error"
                error_code = payload.get("error_code")
                logger.warning("eitaa_api_error", method=method, code=error_code, desc=description)
                raise EitaaAPIError(str(description), error_code)
            return payload.get("result") or {}
