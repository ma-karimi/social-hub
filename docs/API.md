# SocialHub / Codenegar Social API

Multi-tenant API for publishing and inbox across Instagram, Telegram, Bale, and Eitaa.

For platform adapter details see [SOCIAL_API_PLATFORM_GUIDE.md](SOCIAL_API_PLATFORM_GUIDE.md).

## Quick start

```bash
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn social_hub.main:app --reload --port 8000
```

Docs: `/docs` (EN), `/docs/fa` (FA) — live routes on the running server.
Static OpenAPI snapshots: `docs/openapi/openapi.en.json`, `docs/openapi/openapi.fa.json`.
Postman: `docs/postman/SocialHub.postman_collection.json` + `SocialHub.postman_environment.json`.

## Auth

All `/api/v1/social/*` routes require `X-API-Key` (tenant key from `POST /api/v1/tenants`).

Errors:

```json
{ "error_code": "ACCOUNT_NOT_FOUND", "message": "..." }
```

`Accept-Language: fa` switches `message` to Persian (default English).

## Main routes

Base: `/api/v1/social`

| Area | Paths |
|------|-------|
| Accounts | `POST /accounts/connect`, `GET /accounts`, `GET/PATCH/DELETE /accounts/{id}`, `POST /accounts/{id}/test` |
| Instagram connect | `GET /accounts/connect/callback`, `GET /accounts/connect/pages`, `POST /accounts/connect/select` |
| Config | `GET/PATCH /config/instagram` |
| Posts | `POST/GET /posts`, `GET/DELETE /posts/{id}` |
| Media | `POST /media/presign`, `GET /media/relay/{key}` |
| Quota | `GET /accounts/{id}/publishing-quota` |
| Analytics / stories | `/analytics`, `/accounts/{id}/insights`, `/accounts/{id}/stories/...` |
| Inbox | `/inbox/conversations...`, `/inbox/comments...` |
| Automations | `/automations/comment-to-dm`, `/automations/story-reply` |
| Webhooks | `/api/v1/webhooks/social/provider`, `/api/v1/webhooks/social/{platform}/{account_id}` |

Timezone default for scheduled posts: `Asia/Tehran`.

Legacy `/posts` and `/connections` routes have been removed — use `/social` only.
