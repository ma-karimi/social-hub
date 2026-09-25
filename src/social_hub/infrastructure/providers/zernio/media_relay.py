"""Streaming media relay — proxies bytes from upstream CDN without local storage."""

from collections.abc import AsyncIterator

import httpx
import structlog
from fastapi.responses import StreamingResponse

from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import SocialHubError

logger = structlog.get_logger(__name__)


async def stream_upstream(url: str) -> StreamingResponse:
    client = httpx.AsyncClient(timeout=120.0, follow_redirects=True)

    try:
        req = client.build_request("GET", url)
        resp = await client.send(req, stream=True)
    except Exception as exc:
        await client.aclose()
        logger.warning("media_relay_fetch_failed", error=str(exc))
        raise SocialHubError(
            "Failed to fetch media", error_code=ErrorCode.MEDIA_FETCH_FAILED
        ) from exc

    if resp.status_code >= 400:
        await resp.aclose()
        await client.aclose()
        raise SocialHubError(
            "Media not available", error_code=ErrorCode.MEDIA_FETCH_FAILED
        )

    content_type = resp.headers.get("content-type", "application/octet-stream")

    async def iterator() -> AsyncIterator[bytes]:
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(iterator(), media_type=content_type)
