"""Map upstream responses to public Codenegar shapes; scrub provider domains from URLs."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

_ZERNIO_HOST_RE = re.compile(r"(?i)(^|\.)zernio\.com$")


def contains_zernio_domain(value: str) -> bool:
    try:
        host = urlparse(value).hostname or ""
    except Exception:
        return "zernio" in value.lower()
    return bool(_ZERNIO_HOST_RE.search(host)) or "zernio" in host.lower()


def scrub_urls_in_obj(obj: Any, rewrite_fn=None) -> Any:
    """Recursively scrub/rewrite string URLs that point at the upstream CDN."""
    if isinstance(obj, dict):
        return {k: scrub_urls_in_obj(v, rewrite_fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_urls_in_obj(v, rewrite_fn) for v in obj]
    if isinstance(obj, str) and (obj.startswith("http://") or obj.startswith("https://")):
        if contains_zernio_domain(obj):
            if rewrite_fn:
                return rewrite_fn(obj)
            return ""
        return obj
    return obj


def to_snake(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch.lower() if ch.isupper() else ch)
    return "".join(out)


def keys_to_snake(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {to_snake(k): keys_to_snake(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [keys_to_snake(v) for v in obj]
    return obj


def map_presign_response(
    upstream: dict,
    *,
    relay_base_url: str,
    opaque_key: str | None = None,
) -> tuple[dict, str, str]:
    """Return (public_payload, opaque_key, upstream_public_url)."""
    key = opaque_key or uuid4().hex
    upstream_public = upstream.get("publicUrl") or upstream.get("public_url") or ""
    upstream_path = upstream.get("key") or urlparse(upstream_public).path.lstrip("/")
    upload_url = upstream.get("uploadUrl") or upstream.get("upload_url") or ""
    # Prefer keeping upload URL if it doesn't leak brand; otherwise still return it
    # (presigned S3 hosts are typically amazonaws.com — acceptable per plan).
    public_url = f"{relay_base_url.rstrip('/')}/api/v1/social/media/relay/{key}"
    payload = {
        "upload_url": upload_url,
        "public_url": public_url,
        "key": key,
        "expires_in": upstream.get("expiresIn") or upstream.get("expires_in") or 3600,
    }
    return payload, key, upstream_public or f"path:{upstream_path}"


def map_post_response(upstream: dict, *, account_id_map: dict[str, str] | None = None) -> dict:
    """Map upstream post payload to public snake_case without provider fields."""
    post = upstream.get("post") or upstream
    platforms = []
    for p in post.get("platforms") or []:
        ext_id = p.get("accountId") or p.get("account_id")
        mapped_account = (account_id_map or {}).get(ext_id, ext_id)
        platforms.append(
            {
                "platform": p.get("platform"),
                "account_id": mapped_account,
                "status": p.get("status"),
                "platform_post_url": p.get("platformPostUrl") or p.get("platform_post_url"),
                "error": p.get("errorMessage") or p.get("error"),
            }
        )
    return {
        "id": post.get("_id") or post.get("id"),
        "status": post.get("status"),
        "platforms": platforms,
        "content": post.get("content"),
        "metadata": scrub_urls_in_obj(post.get("metadata") or {}),
    }


def map_quota(upstream: dict) -> dict:
    return {
        "quota_usage": upstream.get("quotaUsage", upstream.get("quota_usage")),
        "quota_total": upstream.get("quotaTotal", upstream.get("quota_total")),
        "quota_duration_seconds": upstream.get(
            "quotaDurationSeconds", upstream.get("quota_duration_seconds")
        ),
    }


def platform_specific_to_upstream(data: dict) -> dict:
    """Convert our snake_case platform_specific_data to upstream camelCase."""
    mapping = {
        "content_type": "contentType",
        "share_to_feed": "shareToFeed",
        "collaborators": "collaborators",
        "user_tags": "userTags",
        "trial_params": "trialParams",
        "thumb_offset": "thumbOffset",
        "instagram_thumbnail": "instagramThumbnail",
        "reel_cover": "reelCover",
        "audio_name": "audioName",
        "audio_configuration": "audioConfiguration",
        "mute_audio": "muteAudio",
        "is_ai_generated": "isAiGenerated",
        "is_paid_partnership": "isPaidPartnership",
        "branded_content_sponsors": "brandedContentSponsors",
        "comments_enabled": "commentsEnabled",
        "location_id": "locationId",
        "first_comment": "firstComment",
    }
    out: dict = {}
    for k, v in data.items():
        uk = mapping.get(k, k)
        if k == "user_tags" and isinstance(v, list):
            out[uk] = [
                {
                    "username": t.get("username"),
                    "x": t.get("x"),
                    "y": t.get("y"),
                    "mediaIndex": t.get("media_index", t.get("mediaIndex")),
                }
                for t in v
            ]
        elif k == "audio_configuration" and isinstance(v, dict):
            out[uk] = {
                "audioId": v.get("audio_id", v.get("audioId")),
                "audioVolume": v.get("audio_volume", v.get("audioVolume", 100)),
                "videoVolume": v.get("video_volume", v.get("videoVolume", 100)),
            }
        elif k == "trial_params" and isinstance(v, dict):
            out[uk] = {
                "graduationStrategy": v.get(
                    "graduation_strategy", v.get("graduationStrategy")
                )
            }
        else:
            out[uk] = v
    return out


def normalize_webhook_event(raw: dict) -> dict:
    """Normalize upstream webhook into Codenegar event envelope."""
    event_type = raw.get("type") or raw.get("event") or raw.get("eventType") or "unknown"
    payload = keys_to_snake(scrub_urls_in_obj(raw.get("data") or raw.get("payload") or raw))
    return {
        "event_type": to_snake(str(event_type).replace(".", "_")),
        "payload": payload,
    }
