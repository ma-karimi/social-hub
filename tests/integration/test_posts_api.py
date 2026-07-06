"""Integration tests for the posts API.

Uses httpx.AsyncClient with a FastAPI app backed by a mock container
so no real database or Redis is required.
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.entities.publication import Publication
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.post_type import PostType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.main import create_app
from social_hub.shared.types import TenantContext


def _mock_session():
    """Return a mock AsyncSession context-manager."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    begin_ctx = AsyncMock()
    begin_ctx.__aenter__ = AsyncMock(return_value=None)
    begin_ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=begin_ctx)
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock(return_value=[])
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _mock_container(tenant_id):
    """Build a fully-mocked container."""
    container = MagicMock()
    session = _mock_session()
    container.session_factory.return_value = session

    container.encryptor = MagicMock()
    container.encryptor.decrypt = MagicMock(return_value={"bot_token": "test:token"})
    container.driver_registry = MagicMock()
    container.capability_resolver = MagicMock()
    container.arq_redis = MagicMock()
    container.arq_redis.enqueue_job = AsyncMock()
    return container


def make_test_app(tenant_id=None, tenant_name="Test Store"):
    """Create a FastAPI app with an injected mock container."""
    tid = tenant_id or uuid4()

    container = _mock_container(tid)

    from social_hub.shared.utils import hash_api_key

    TEST_API_KEY = "test-api-key-for-integration"
    api_key_hash = hash_api_key(TEST_API_KEY)

    from social_hub.domain.entities.tenant import Tenant

    mock_tenant = Tenant(
        id=tid,
        name=tenant_name,
        api_key_hash=api_key_hash,
        is_active=True,
        settings={},
    )

    # repo mocks injected via session scalars
    tenant_repo_mock = MagicMock()
    tenant_repo_mock.get_by_api_key_hash = AsyncMock(return_value=mock_tenant)

    from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo

    @asynccontextmanager
    async def test_lifespan(app):
        app.state.container = container
        yield

    app = create_app(lifespan_override=test_lifespan)

    # Patch get_tenant_context dependency to use our mock tenant
    from social_hub.api.deps import get_tenant_context

    async def override_get_tenant_context():
        return TenantContext(tenant_id=tid, tenant_name=tenant_name)

    app.dependency_overrides[get_tenant_context] = override_get_tenant_context

    return app, container, tid, TEST_API_KEY


@pytest.mark.asyncio
async def test_health_endpoint():
    @asynccontextmanager
    async def dummy_lifespan(app):
        yield

    app = create_app(lifespan_override=dummy_lifespan)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_publish_requires_api_key():
    @asynccontextmanager
    async def dummy_lifespan(app):
        container = MagicMock()
        session = _mock_session()
        container.session_factory.return_value = session
        app.state.container = container
        yield

    app = create_app(lifespan_override=dummy_lifespan)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/posts/publish-product",
            json={
                "platforms": ["telegram"],
                "content": {"title": "T", "body": "B"},
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_posts_returns_empty_without_data():
    app, container, tenant_id, api_key = make_test_app()

    from social_hub.infrastructure.db.repositories.post_repo import SQLAlchemyPostRepo

    async def mock_list(tenant_id, limit=50, offset=0):
        return []

    with __import__("unittest.mock", fromlist=["patch"]).patch.object(
        SQLAlchemyPostRepo, "list_by_tenant", new=mock_list
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/posts",
                headers={"x-api-key": api_key},
            )

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_post_not_found_returns_404():
    app, container, tenant_id, api_key = make_test_app()
    missing_id = uuid4()

    from social_hub.infrastructure.db.repositories.post_repo import SQLAlchemyPostRepo
    from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo

    async def mock_get(self_arg, tid, pid):
        return None

    with __import__("unittest.mock", fromlist=["patch"]).patch.object(
        SQLAlchemyPostRepo, "get_by_id", new=mock_get
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/posts/{missing_id}",
                headers={"x-api-key": api_key},
            )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_post_not_found_returns_404():
    app, container, tenant_id, api_key = make_test_app()
    missing_id = uuid4()

    from social_hub.infrastructure.db.repositories.post_repo import SQLAlchemyPostRepo

    async def mock_get(self_arg, tid, pid):
        return None

    with __import__("unittest.mock", fromlist=["patch"]).patch.object(
        SQLAlchemyPostRepo, "get_by_id", new=mock_get
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(
                f"/api/v1/posts/{missing_id}",
                headers={"x-api-key": api_key},
            )

    assert resp.status_code == 404
