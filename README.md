# SocialHub

Multi-Tenant Social Publishing & Integration Platform.

## Architecture

- **Language / Framework:** Python 3.12 + FastAPI
- **Database:** PostgreSQL 16 (SQLAlchemy 2.0 async + Alembic)
- **Queue:** Arq (Redis-backed)
- **Encryption:** Fernet (cryptography library)
- **Auth:** API Key per Tenant (header `X-API-Key`)

## Local Setup (no Docker)

### Prerequisites

| Service    | Version | macOS install             |
|------------|---------|---------------------------|
| Python     | 3.12+   | `brew install python@3.12`|
| PostgreSQL | 16+     | `brew install postgresql@16` |
| Redis      | 7+      | `brew install redis`      |

### Quick start (one command)

```bash
./scripts/dev_up.sh
```

This script will:
- create `.venv` and install dependencies
- create `.env` if missing (with `ENCRYPTION_KEY`)
- create the PostgreSQL database if it doesn't exist
- run migrations and seed demo data
- start the API server and keep the Arq worker running

Credentials are saved to `.dev-seed.json` (gitignored).

### Manual setup

### 1. Create and activate virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL, REDIS_URL, and generate ENCRYPTION_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Create database and run migrations

```bash
createdb socialhub
alembic upgrade head
```

### 4. Start API server

```bash
uvicorn social_hub.main:app --reload --port 8000
```

### 5. Start background worker (separate terminal)

```bash
arq social_hub.infrastructure.queue.worker.WorkerSettings
```

## API Documentation

- **Full guide:** [docs/API.md](docs/API.md)
- **Postman collection:** [docs/postman/SocialHub.postman_collection.json](docs/postman/SocialHub.postman_collection.json)
- **Postman environment:** [docs/postman/SocialHub.postman_environment.json](docs/postman/SocialHub.postman_environment.json)
- **Interactive docs:** `http://localhost:8000/docs` (Swagger UI)

## API Overview

Base URL: `/api/v1`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/posts/publish-product` | Publish a product post |
| POST | `/posts/publish` | Publish a normal post |
| PATCH | `/posts/{post_id}` | Edit a published post |
| DELETE | `/posts/{post_id}` | Delete from all platforms |
| GET | `/posts/{post_id}` | Get publication status |
| POST | `/connections` | Create platform connection |
| GET | `/connections` | List connections |
| PATCH | `/connections/{id}` | Update connection |
| DELETE | `/connections/{id}` | Remove connection |
| POST | `/webhooks/telegram/{connection_id}` | Telegram webhook ingress |

## Adding a New Platform

1. Add value to `PlatformType` enum
2. Define `PlatformCapabilities` in `infrastructure/platforms/capabilities.py`
3. Implement `XxxDriver(PlatformDriver)` in `infrastructure/platforms/xxx/`
4. Register driver in `container.py`
5. Add webhook route in `api/v1/webhooks/` (if applicable)

## Production

```bash
# API (multiple workers behind nginx)
uvicorn social_hub.main:app --workers 4 --port 8000

# Worker as systemd service
arq social_hub.infrastructure.queue.worker.WorkerSettings
```
