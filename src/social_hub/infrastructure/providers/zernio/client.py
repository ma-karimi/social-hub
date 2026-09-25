"""Thin async HTTP client for the upstream Instagram provider (internal only)."""

from typing import Any

import httpx
import structlog

from social_hub.infrastructure.providers.zernio.errors import ZernioAPIError

logger = structlog.get_logger(__name__)


class ZernioHttpClient:
    def __init__(self, api_key: str, base_url: str, *, timeout: float = 60.0) -> None:
        self._api_key = api_key
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        headers: dict | None = None,
        expected_statuses: set[int] | None = None,
    ) -> tuple[int, dict | list | None]:
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers=self._headers(headers),
            )
        body: dict | list | None
        try:
            body = resp.json() if resp.content else None
        except Exception:
            body = None

        allowed = expected_statuses or {200, 201, 202, 204, 207}
        if resp.status_code not in allowed:
            logger.warning(
                "upstream_http_error",
                status=resp.status_code,
                path=path,
                method=method,
            )
            msg = "Upstream request failed"
            if isinstance(body, dict):
                msg = str(body.get("error") or body.get("message") or msg)
            raise ZernioAPIError(msg, status_code=resp.status_code, body=body if isinstance(body, dict) else {})
        return resp.status_code, body if isinstance(body, (dict, list)) else None

    async def get(self, path: str, **kwargs) -> tuple[int, dict | list | None]:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> tuple[int, dict | list | None]:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> tuple[int, dict | list | None]:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> tuple[int, dict | list | None]:
        return await self.request("DELETE", path, **kwargs)

    # --- Connect ---
    async def connect_instagram(
        self,
        profile_id: str,
        redirect_url: str,
        *,
        login_method: str = "instagram_login",
        headless: bool = True,
    ) -> dict:
        params = {
            "profileId": profile_id,
            "redirect_url": redirect_url,
            "loginMethod": login_method,
        }
        if headless:
            params["headless"] = "true"
        _, body = await self.get("/v1/connect/instagram", params=params)
        return body if isinstance(body, dict) else {}

    async def list_connect_pages(self, connect_token: str) -> dict:
        _, body = await self.get(
            "/v1/connect/pages",
            params={"connect_token": connect_token},
            expected_statuses={200},
        )
        return body if isinstance(body, dict) else {}

    async def select_connect_page(self, connect_token: str, page_id: str) -> dict:
        _, body = await self.post(
            "/v1/connect/select-page",
            json={"connect_token": connect_token, "pageId": page_id},
            expected_statuses={200, 201},
        )
        return body if isinstance(body, dict) else {}

    # --- Quota / posts / media ---
    async def get_publishing_limit(self, account_id: str) -> dict:
        _, body = await self.get(f"/v1/accounts/{account_id}/instagram/publishing-limit")
        return body if isinstance(body, dict) else {}

    async def create_post(self, payload: dict, *, request_id: str | None = None) -> tuple[int, dict]:
        headers = {}
        if request_id:
            headers["x-request-id"] = request_id
        status, body = await self.post(
            "/v1/posts",
            json=payload,
            headers=headers or None,
            expected_statuses={200, 201, 207, 409},
        )
        return status, body if isinstance(body, dict) else {}

    async def get_post(self, post_id: str) -> dict:
        _, body = await self.get(f"/v1/posts/{post_id}")
        return body if isinstance(body, dict) else {}

    async def update_post(self, post_id: str, payload: dict) -> dict:
        _, body = await self.put(f"/v1/posts/{post_id}", json=payload)
        return body if isinstance(body, dict) else {}

    async def delete_post(self, post_id: str) -> None:
        await self.delete(f"/v1/posts/{post_id}", expected_statuses={200, 204})

    async def list_posts(self, params: dict | None = None) -> dict:
        _, body = await self.get("/v1/posts", params=params)
        return body if isinstance(body, dict) else {}

    async def media_presign(self, filename: str, content_type: str) -> dict:
        _, body = await self.post(
            "/v1/media/presign",
            json={"filename": filename, "contentType": content_type},
        )
        return body if isinstance(body, dict) else {}

    # --- Analytics / stories ---
    async def get_analytics(self, params: dict | None = None) -> dict:
        _, body = await self.get("/v1/analytics", params=params or {"platform": "instagram"})
        return body if isinstance(body, dict) else {}

    async def get_account_insights(self, account_id: str, params: dict | None = None) -> dict:
        _, body = await self.get(
            f"/v1/accounts/{account_id}/instagram/insights", params=params
        )
        return body if isinstance(body, dict) else {}

    async def list_stories(self, account_id: str) -> dict:
        _, body = await self.get(f"/v1/accounts/{account_id}/instagram/stories")
        return body if isinstance(body, dict) else {}

    async def get_story_insights(self, account_id: str, story_id: str) -> dict:
        _, body = await self.get(
            f"/v1/accounts/{account_id}/instagram/stories/{story_id}/insights"
        )
        return body if isinstance(body, dict) else {}

    async def search_audio(self, account_id: str, params: dict | None = None) -> dict:
        _, body = await self.get(f"/v1/accounts/{account_id}/instagram/audio", params=params)
        return body if isinstance(body, dict) else {}

    async def get_audio(self, account_id: str, audio_id: str) -> dict:
        _, body = await self.get(f"/v1/accounts/{account_id}/instagram/audio/{audio_id}")
        return body if isinstance(body, dict) else {}

    # --- Inbox / ice breakers / follow ---
    async def get_follow_status(self, account_id: str, user_id: str) -> dict:
        _, body = await self.get(f"/v1/accounts/{account_id}/follow-status/{user_id}")
        return body if isinstance(body, dict) else {}

    async def get_ice_breakers(self, account_id: str) -> dict:
        _, body = await self.get(f"/v1/accounts/{account_id}/instagram-ice-breakers")
        return body if isinstance(body, dict) else {}

    async def put_ice_breakers(self, account_id: str, ice_breakers: list[str]) -> dict:
        _, body = await self.put(
            f"/v1/accounts/{account_id}/instagram-ice-breakers",
            json={"iceBreakers": ice_breakers},
        )
        return body if isinstance(body, dict) else {}

    async def delete_ice_breakers(self, account_id: str) -> None:
        await self.delete(
            f"/v1/accounts/{account_id}/instagram-ice-breakers",
            expected_statuses={200, 204},
        )

    async def list_conversations(self, params: dict | None = None) -> dict:
        _, body = await self.get("/v1/inbox/conversations", params=params)
        return body if isinstance(body, dict) else {}

    async def get_conversation(self, conversation_id: str) -> dict:
        _, body = await self.get(f"/v1/inbox/conversations/{conversation_id}")
        return body if isinstance(body, dict) else {}

    async def send_message(self, conversation_id: str, payload: dict) -> dict:
        _, body = await self.post(
            f"/v1/inbox/conversations/{conversation_id}/messages",
            json=payload,
        )
        return body if isinstance(body, dict) else {}

    async def add_reaction(self, conversation_id: str, message_id: str, payload: dict) -> dict:
        _, body = await self.post(
            f"/v1/inbox/conversations/{conversation_id}/messages/{message_id}/reaction",
            json=payload,
        )
        return body if isinstance(body, dict) else {}

    async def remove_reaction(self, conversation_id: str, message_id: str) -> None:
        await self.delete(
            f"/v1/inbox/conversations/{conversation_id}/messages/{message_id}/reaction",
            expected_statuses={200, 204},
        )

    async def list_comments(self, params: dict | None = None) -> dict:
        _, body = await self.get("/v1/inbox/comments", params=params)
        return body if isinstance(body, dict) else {}

    async def create_comment(self, payload: dict) -> dict:
        _, body = await self.post("/v1/inbox/comments", json=payload)
        return body if isinstance(body, dict) else {}

    async def reply_comment(self, comment_id: str, payload: dict) -> dict:
        _, body = await self.post(f"/v1/inbox/comments/{comment_id}/replies", json=payload)
        return body if isinstance(body, dict) else {}

    async def delete_comment(self, comment_id: str) -> None:
        await self.delete(f"/v1/inbox/comments/{comment_id}", expected_statuses={200, 204})

    async def hide_comment(self, comment_id: str, payload: dict) -> dict:
        _, body = await self.post(f"/v1/inbox/comments/{comment_id}/hide", json=payload)
        return body if isinstance(body, dict) else {}

    async def private_reply_comment(self, comment_id: str, payload: dict) -> dict:
        _, body = await self.post(
            f"/v1/inbox/comments/{comment_id}/private-reply", json=payload
        )
        return body if isinstance(body, dict) else {}

    async def list_comment_automations(self, params: dict | None = None) -> dict:
        _, body = await self.get("/v1/comment-automations", params=params)
        return body if isinstance(body, dict) else {}

    async def create_comment_automation(self, payload: dict) -> dict:
        _, body = await self.post("/v1/comment-automations", json=payload)
        return body if isinstance(body, dict) else {}

    async def update_comment_automation(self, automation_id: str, payload: dict) -> dict:
        _, body = await self.put(f"/v1/comment-automations/{automation_id}", json=payload)
        return body if isinstance(body, dict) else {}

    async def delete_comment_automation(self, automation_id: str) -> None:
        await self.delete(
            f"/v1/comment-automations/{automation_id}", expected_statuses={200, 204}
        )

    async def list_story_reply_automations(self, params: dict | None = None) -> dict:
        _, body = await self.get("/v1/story-reply-automations", params=params)
        return body if isinstance(body, dict) else {}

    async def create_story_reply_automation(self, payload: dict) -> dict:
        _, body = await self.post("/v1/story-reply-automations", json=payload)
        return body if isinstance(body, dict) else {}

    async def update_story_reply_automation(self, automation_id: str, payload: dict) -> dict:
        _, body = await self.put(
            f"/v1/story-reply-automations/{automation_id}", json=payload
        )
        return body if isinstance(body, dict) else {}

    async def delete_story_reply_automation(self, automation_id: str) -> None:
        await self.delete(
            f"/v1/story-reply-automations/{automation_id}", expected_statuses={200, 204}
        )

    async def connect_ads(self, platform: str = "instagram") -> dict:
        _, body = await self.post(
            "/v1/connect/connect-ads",
            params={"platform": platform},
            expected_statuses={200, 201},
        )
        return body if isinstance(body, dict) else {}
