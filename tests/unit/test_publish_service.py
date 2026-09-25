import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from social_hub.application.services.capability_resolver import CapabilityResolver
from social_hub.application.services.publish_service import PublishService
from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.entities.publication import Publication
from social_hub.domain.exceptions import ConnectionNotFoundError, DuplicatePostError
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.post_type import PostType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.shared.types import TenantContext


def make_service(
    existing_post=None,
    connection=None,
    created_post=None,
    created_publication=None,
):
    tenant_id = uuid4()
    conn_id = uuid4()

    default_connection = PlatformConnection(
        id=conn_id,
        tenant_id=tenant_id,
        platform_type=PlatformType.TELEGRAM,
        credentials_encrypted=b"enc",
        settings={"channel_id": "@ch"},
        is_active=True,
    )

    post_repo = MagicMock()
    post_repo.get_by_external_ref = AsyncMock(return_value=existing_post)
    default_post = Post(
        id=uuid4(),
        tenant_id=tenant_id,
        post_type=PostType.PRODUCT,
        content=PostContent(title="T", body="B"),
        status="draft",
    )
    post_repo.create = AsyncMock(return_value=created_post or default_post)

    conn_repo = MagicMock()
    conn_repo.get_by_platform = AsyncMock(return_value=connection or default_connection)

    pub_repo = MagicMock()
    default_pub = Publication(
        id=uuid4(),
        post_id=default_post.id,
        account_id=conn_id,
        status=PublicationStatus.PENDING,
    )
    pub_repo.create = AsyncMock(return_value=created_publication or default_pub)

    btn_repo = MagicMock()
    btn_repo.create_many = AsyncMock(return_value=[])

    arq_pool = MagicMock()
    arq_pool.enqueue_job = AsyncMock()

    service = PublishService(
        post_repo=post_repo,
        connection_repo=conn_repo,
        publication_repo=pub_repo,
        button_repo=btn_repo,
        capability_resolver=CapabilityResolver(),
        arq_pool=arq_pool,
    )
    return service, tenant_id, arq_pool


@pytest.mark.asyncio
async def test_publish_product_enqueues_job():
    service, tenant_id, arq_pool = make_service()
    ctx = TenantContext(tenant_id=tenant_id, tenant_name="Test")
    content = PostContent(title="Product A", body="Great product", price=50000)
    result = await service.publish_product(
        tenant_ctx=ctx,
        platforms=[PlatformType.TELEGRAM],
        content=content,
        buttons_data=[],
    )
    assert result["post_id"]
    assert len(result["publications"]) == 1
    arq_pool.enqueue_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_raises_on_duplicate_external_ref():
    existing_post = Post(
        id=uuid4(), tenant_id=uuid4(), post_type=PostType.PRODUCT,
        content=PostContent(title="T", body="B"), status="published",
    )
    service, tenant_id, _ = make_service(existing_post=existing_post)
    ctx = TenantContext(tenant_id=tenant_id, tenant_name="Test")
    content = PostContent(title="T", body="B")

    with pytest.raises(DuplicatePostError):
        await service.publish_product(
            tenant_ctx=ctx,
            platforms=[PlatformType.TELEGRAM],
            content=content,
            buttons_data=[],
            external_ref="product-1",
        )


@pytest.mark.asyncio
async def test_publish_raises_if_no_active_connection():
    service, tenant_id, _ = make_service(connection=None)
    service._connection_repo.get_by_platform = AsyncMock(return_value=None)

    ctx = TenantContext(tenant_id=tenant_id, tenant_name="Test")
    content = PostContent(title="T", body="B")

    with pytest.raises(ConnectionNotFoundError):
        await service.publish_product(
            tenant_ctx=ctx,
            platforms=[PlatformType.TELEGRAM],
            content=content,
            buttons_data=[],
        )
