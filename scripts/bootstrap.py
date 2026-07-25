#!/usr/bin/env python3
"""Database bootstrap and demo seed for local development."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = ROOT / ".dev-seed.json"


def ensure_env_file() -> None:
    env_path = ROOT / ".env"
    example_path = ROOT / ".env.example"

    if env_path.exists():
        _ensure_encryption_key(env_path)
        return

    if not example_path.exists():
        print("❌ .env.example not found", file=sys.stderr)
        sys.exit(1)

    content = example_path.read_text()
    if "ENCRYPTION_KEY=" in content and not content.split("ENCRYPTION_KEY=")[1].split("\n")[0].strip():
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        content = content.replace("ENCRYPTION_KEY=", f"ENCRYPTION_KEY={key}", 1)

    env_path.write_text(content)
    print("✓ Created .env from .env.example")


def _ensure_encryption_key(env_path: Path) -> None:
    lines = env_path.read_text().splitlines()
    changed = False
    new_lines: list[str] = []

    for line in lines:
        if line.startswith("ENCRYPTION_KEY=") and not line.removeprefix("ENCRYPTION_KEY=").strip():
            from cryptography.fernet import Fernet

            new_lines.append(f"ENCRYPTION_KEY={Fernet.generate_key().decode()}")
            changed = True
        else:
            new_lines.append(line)

    if changed:
        env_path.write_text("\n".join(new_lines) + "\n")
        print("✓ Generated ENCRYPTION_KEY in .env")


def _parse_database_url(database_url: str) -> tuple[str, str, str | None, int, str]:
    """Return (user, password, host, port, db_name) from SQLAlchemy async URL."""
    from sqlalchemy.engine.url import make_url

    url = make_url(database_url)
    db_name = url.database
    if not db_name:
        raise ValueError("DATABASE_URL has no database name")

    return (
        url.username or "postgres",
        url.password or "",
        url.host or "localhost",
        url.port or 5432,
        db_name,
    )


async def ensure_database(database_url: str) -> str:
    import asyncpg
    import getpass

    user, password, host, port, db_name = _parse_database_url(database_url)

    candidates: list[tuple[str, str | None]] = [(user, password or None)]
    system_user = getpass.getuser()
    if system_user != user:
        candidates.append((system_user, None))

    last_error: Exception | None = None
    conn = None
    connected_as: str | None = None

    for candidate_user, candidate_password in candidates:
        try:
            conn = await asyncpg.connect(
                user=candidate_user,
                password=candidate_password,
                host=host,
                port=port,
                database="postgres",
            )
            connected_as = candidate_user
            break
        except Exception as exc:
            last_error = exc

    if conn is None:
        print(f"❌ Cannot connect to PostgreSQL ({host}:{port}): {last_error}", file=sys.stderr)
        print("   Make sure PostgreSQL is running.", file=sys.stderr)
        print("   Tip: update DATABASE_URL in .env to match your local user, e.g.:", file=sys.stderr)
        print(f"        postgresql+asyncpg://{system_user}@localhost:5432/socialhub", file=sys.stderr)
        sys.exit(1)

    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name,
        )
        if exists:
            print(f"✓ Database '{db_name}' already exists (connected as {connected_as})")
        else:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✓ Created database '{db_name}' (connected as {connected_as})")
    finally:
        await conn.close()

    return _maybe_fix_database_url(connected_as, database_url)


def _maybe_fix_database_url(connected_as: str, database_url: str) -> str:
    """If we connected with a different user, update DATABASE_URL in .env."""
    user, password, host, port, db_name = _parse_database_url(database_url)
    if user == connected_as:
        return database_url

    if password:
        new_url = f"postgresql+asyncpg://{connected_as}:{password}@{host}:{port}/{db_name}"
    else:
        new_url = f"postgresql+asyncpg://{connected_as}@{host}:{port}/{db_name}"

    env_path = ROOT / ".env"
    if env_path.exists():
        text = env_path.read_text()
        import re

        updated = re.sub(
            r"^DATABASE_URL=.*$",
            f"DATABASE_URL={new_url}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if updated != text:
            env_path.write_text(updated)
            print(f"✓ Updated DATABASE_URL in .env to use user '{connected_as}'")

    return new_url


def run_migrations() -> None:
    import subprocess

    alembic = ROOT / ".venv" / "bin" / "alembic"
    if not alembic.exists():
        alembic = "alembic"

    result = subprocess.run(
        [str(alembic), "upgrade", "head"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        print("❌ Alembic migration failed", file=sys.stderr)
        sys.exit(1)
    print("✓ Migrations applied")


async def seed_demo_data() -> dict:
    from social_hub.application.services.connection_service import ConnectionService
    from social_hub.application.services.tenant_service import TenantService
    from social_hub.config import get_settings
    from social_hub.domain.entities.post import Post, PostContent, PostStatus
    from social_hub.domain.value_objects.platform_type import PlatformType
    from social_hub.domain.value_objects.post_type import PostType
    from social_hub.infrastructure.db.repositories.connection_repo import SQLAlchemyConnectionRepo
    from social_hub.infrastructure.db.repositories.post_repo import SQLAlchemyPostRepo
    from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo
    from social_hub.infrastructure.db.session import create_session_factory
    from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor

    if SEED_FILE.exists():
        data = json.loads(SEED_FILE.read_text())
        print(f"✓ Demo data already seeded (tenant: {data.get('tenant_name')})")
        return data

    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    encryptor = FernetEncryptor(settings.encryption_key)

    async with session_factory() as session:
        async with session.begin():
            tenant_repo = SQLAlchemyTenantRepo(session)
            existing = await tenant_repo.list_all()
            if existing:
                print(f"✓ Database has {len(existing)} tenant(s), skipping seed")
                return {"skipped": True, "tenant_count": len(existing)}

            tenant_service = TenantService(tenant_repo)
            tenant, api_key = await tenant_service.create_tenant(
                name="فروشگاه دمو",
                settings={
                    "locale": "fa",
                    "webhook_callback_url": "http://localhost:3000/webhooks/socialhub",
                },
            )

            connection_service = ConnectionService(
                connection_repo=SQLAlchemyConnectionRepo(session),
                encryptor=encryptor,
            )
            from social_hub.shared.types import TenantContext

            tenant_ctx = TenantContext(tenant_id=tenant.id, tenant_name=tenant.name)
            connection = await connection_service.create_connection(
                tenant_ctx=tenant_ctx,
                platform_type=PlatformType.TELEGRAM,
                credentials={"bot_token": "0000000000:DEV_PLACEHOLDER_REPLACE_ME"},
                settings={
                    "channel_id": "@your_channel",
                    "webhook_secret": "dev-webhook-secret",
                },
            )

            post_repo = SQLAlchemyPostRepo(session)
            product_post = Post.create(
                tenant_id=tenant.id,
                post_type=PostType.PRODUCT,
                content=PostContent(
                    title="کفش ورزشی نایک",
                    body="کفش مناسب دویدن با کیفیت عالی.",
                    price=2_500_000,
                    currency="IRR",
                    images=["https://picsum.photos/seed/nike-shoe/800/600"],
                    metadata={"category": "shoes"},
                ),
                external_ref="demo-product-001",
            )
            product_post.status = PostStatus.DRAFT
            await post_repo.create(product_post)

            normal_post = Post.create(
                tenant_id=tenant.id,
                post_type=PostType.NORMAL,
                content=PostContent(
                    title="تخفیف آخر هفته",
                    body="تا ۳۰٪ تخفیف روی همه محصولات — فقط تا یکشنبه!",
                    images=[],
                ),
                external_ref="demo-announcement-001",
            )
            normal_post.status = PostStatus.DRAFT
            await post_repo.create(normal_post)

    data = {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "api_key": api_key,
        "connection_id": str(connection.id),
        "sample_posts": {
            "product": str(product_post.id),
            "announcement": str(normal_post.id),
        },
    }
    SEED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print("✓ Demo data seeded")
    return data


def check_redis(redis_url: str) -> bool:
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        return True
    except Exception:
        return False


def print_summary(seed: dict, redis_ok: bool) -> None:
    print()
    print("=" * 56)
    print("  SocialHub — آماده برای توسعه")
    print("=" * 56)

    if seed.get("skipped"):
        print(f"  Tenants in DB: {seed['tenant_count']}")
        if SEED_FILE.exists():
            saved = json.loads(SEED_FILE.read_text())
            print(f"  API Key:       {saved.get('api_key', '(see .dev-seed.json)')}")
            print(f"  Tenant ID:     {saved.get('tenant_id')}")
            print(f"  Connection ID: {saved.get('connection_id')}")
    else:
        print(f"  API Key:       {seed.get('api_key')}")
        print(f"  Tenant ID:     {seed.get('tenant_id')}")
        print(f"  Connection ID: {seed.get('connection_id')}")
        print(f"  Seed file:     {SEED_FILE}")

    print()
    print("  API:     http://localhost:8000")
    print("  Docs:    http://localhost:8000/docs")
    print("  Health:  http://localhost:8000/health")
    print()
    if not redis_ok:
        print("  ⚠ Redis is not reachable — start it: brew services start redis")
    print("  Worker will stay in foreground. Ctrl+C stops everything.")
    print("=" * 56)
    print()


async def main() -> None:
    os.chdir(ROOT)

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    from social_hub.config import get_settings

    ensure_env_file()
    load_dotenv(ROOT / ".env", override=True)
    settings = get_settings()

    await ensure_database(settings.database_url)
    load_dotenv(ROOT / ".env", override=True)
    settings = get_settings()
    run_migrations()

    redis_ok = check_redis(settings.redis_url)
    if not redis_ok:
        print("⚠ Redis not available — worker may fail until Redis is started")

    seed = await seed_demo_data()
    print_summary(seed, redis_ok)


if __name__ == "__main__":
    asyncio.run(main())
