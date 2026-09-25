"""Legacy posts API integration tests were removed with /posts routes.

Minimal smoke: health + openapi brand safety.
"""
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from social_hub.main import create_app


@asynccontextmanager
async def _noop_lifespan(app):
    app.state.container = None
    yield


@pytest.mark.asyncio
async def test_health():
    app = create_app(lifespan_override=_noop_lifespan)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_openapi_en_no_provider_brand():
    app = create_app(lifespan_override=_noop_lifespan)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    assert "zernio" not in resp.text.lower()
    assert "Codenegar" in resp.json()["info"]["title"]
