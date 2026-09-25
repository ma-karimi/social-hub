# Codenegar Social API — Platform Guide

This document describes the unified `/api/v1/social/*` surface used by all platforms.

## Supported platforms (current)

| Platform | Connect model | Publish | Inbox | Analytics | Notes |
|----------|---------------|---------|-------|-----------|-------|
| Instagram | OAuth (`instagram_login` default, `facebook_login` optional) | Yes (schedule/draft) | Yes | Yes | Upstream HTTP provider abstracted as Codenegar |
| Telegram | Credential (`bot_token` + `channel_id`) | Yes | Callbacks via webhook | No | |
| Bale | Credential | Yes | Callbacks via webhook | No | |
| Eitaa | Credential | Publish only | No | No | |

## Architecture

- Public API never mentions upstream provider brands or raw upstream field names.
- `PlatformAdapter` contract lives under `application/adapters/`.
- Instagram adapter uses a thin internal HTTP client (`infrastructure/providers/zernio/`, internal-only package path).
- Telegram/Bale/Eitaa adapters wrap existing bot HTTP clients.

## Connect

### Instagram (headless default)

1. `POST /api/v1/social/accounts/connect` with `{platform, redirect_url, login_method?, mode?}`
2. Redirect user to `auth_url`
3. After OAuth, consumer receives `connect_token` on `redirect_url`
4. Optional: `GET .../connect/pages` + `POST .../connect/select` for Facebook Login page picker

### Telegram / Bale / Eitaa

`POST /api/v1/social/accounts/connect` with:

```json
{
  "platform": "telegram",
  "credentials": {"bot_token": "..."},
  "settings": {"channel_id": "@channel", "webhook_secret": "..."}
}
```

Returns `account_id` immediately (`mode=credentials`).

## Facebook Login feature config (Instagram)

Defaults are **enabled** (`true`). Tenants may disable features via:

`GET/PATCH /api/v1/social/config/instagram`

```json
{
  "facebook_login_features": {
    "ads": true,
    "audio_configuration": true,
    "paid_partnership": true,
    "branded_content_sponsors": true
  }
}
```

Gate rules:

- `instagram_login` accounts → always `FEATURE_REQUIRES_FACEBOOK_LOGIN`
- `facebook_login` + feature disabled → `FEATURE_DISABLED_FOR_TENANT` (ads endpoint may return 404)

## Media

- Prefer customer CDN URLs in `media_items`.
- Fallback: `POST /api/v1/social/media/presign` then PUT to `upload_url`.
- `public_url` is always a Codenegar relay: `GET /api/v1/social/media/relay/{key}` (streaming, no local storage).

## Posts

`POST /api/v1/social/posts` — default `timezone` is `Asia/Tehran`. Send `X-Request-Id` for idempotency. Partial failure returns HTTP 207.

## Webhooks

- Instagram lifecycle: `POST /api/v1/webhooks/social/provider`
- Telegram/Bale: `POST /api/v1/webhooks/social/{platform}/{account_id}`

Events are forwarded to tenant `settings.webhook_callback_url` when set.

## Adding a fifth platform

1. Implement `PlatformAdapter` with `SocialCapabilities`
2. Register in `container._register_adapters` / lazy registry
3. Extend OpenAPI descriptions (en + fa)
4. Add unit tests for connect + publish paths
5. Never leak third-party provider names in public schemas

## Docs

Swagger UI and OpenAPI are **live HTTP routes on the running API server** (not folders under `docs/`):

| What | URL (server running) | Static snapshot on disk |
|------|----------------------|-------------------------|
| English Swagger UI | `GET /docs` | — |
| English OpenAPI | `GET /openapi.json` | [`docs/openapi/openapi.en.json`](openapi/openapi.en.json) |
| Persian Swagger UI | `GET /docs/fa` | — |
| Persian OpenAPI | `GET /openapi.fa.json` | [`docs/openapi/openapi.fa.json`](openapi/openapi.fa.json) |

Example with local server: `http://localhost:8000/docs` and `http://localhost:8000/docs/fa`.

Postman: import [`docs/postman/SocialHub.postman_collection.json`](postman/SocialHub.postman_collection.json) + [`SocialHub.postman_environment.json`](postman/SocialHub.postman_environment.json).

Errors: `{ "error_code": "...", "message": "..." }` switched by `Accept-Language` (default English).
