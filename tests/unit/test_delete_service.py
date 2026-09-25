import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from social_hub.application.services.delete_service import DeleteService
from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.entities.publication import Publication
from social_hub.domain.exceptions import PostNotFoundError
from social_hub.domain.value_objects.post_type import PostType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.shared.types import TenantContext


def make_service(existing_post=None, publications=None):
    tenant_id = uuid4()
    post_id = uuid4()
    conn_id = uuid4()

    default_post = Post(
        id=post_id,
        tenant_id=tenant_id,
        post_type=PostType.PRODUCT,
        content=PostContent(title="T", body="B"),
        status="published",
    )

    post_repo = MagicMock()
    post_repo.get_by_id = AsyncMock(return_value=existing_post if existing_post is not None else default_post)

    default_publications = [
        Publication(
            id=uuid4(),
            post_id=post_id,
            account_id=conn_id,
            status=PublicationStatus.PUBLISHED,
        )
    ]

    pub_repo = MagicMock()
    pub_repo.list_by_post = AsyncMock(
        return_value=publications if publications is not None else default_publications
    )

    arq_pool = MagicMock()
    arq_pool.enqueue_job = AsyncMock()

    service = DeleteService(
        post_repo=post_repo,
        publication_repo=pub_repo,
        arq_pool=arq_pool,
    )

    ctx = TenantContext(tenant_id=tenant_id, tenant_name="TestTenant")
    return service, ctx, post_id, arq_pool


@pytest.mark.asyncio
async def test_delete_post_enqueues_job():
    service, ctx, post_id, arq_pool = make_service()

    result = await service.delete_post(tenant_ctx=ctx, post_id=post_id)

    assert result["post_id"] == str(post_id)
    assert result["delete_enqueued"] == 1
    arq_pool.enqueue_job.assert_awaited_once_with("delete_job", str(post_id))


@pytest.mark.asyncio
async def test_delete_post_not_found_raises():
    service, ctx, post_id, _ = make_service()
    service._post_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PostNotFoundError):
        await service.delete_post(tenant_ctx=ctx, post_id=post_id)


@pytest.mark.asyncio
async def test_delete_post_no_published_does_not_enqueue():
    service, ctx, post_id, arq_pool = make_service(publications=[])

    result = await service.delete_post(tenant_ctx=ctx, post_id=post_id)

    assert result["delete_enqueued"] == 0
    arq_pool.enqueue_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_only_enqueues_once_for_multiple_publications():
    post_id = uuid4()
    conn_id = uuid4()
    pubs = [
        Publication(id=uuid4(), post_id=post_id, account_id=conn_id, status=PublicationStatus.PUBLISHED),
        Publication(id=uuid4(), post_id=post_id, account_id=uuid4(), status=PublicationStatus.PUBLISHED),
    ]
    service, ctx, post_id, arq_pool = make_service(publications=pubs)

    await service.delete_post(tenant_ctx=ctx, post_id=post_id)

    arq_pool.enqueue_job.assert_awaited_once_with("delete_job", str(post_id))
