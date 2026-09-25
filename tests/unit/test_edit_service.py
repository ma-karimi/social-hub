import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from social_hub.application.services.edit_service import EditService
from social_hub.application.services.capability_resolver import CapabilityResolver
from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.entities.publication import Publication
from social_hub.domain.exceptions import PostNotFoundError
from social_hub.domain.value_objects.platform_type import PlatformType
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
        content=PostContent(title="Old Title", body="Old body"),
        status="published",
    )

    post_repo = MagicMock()
    post_repo.get_by_id = AsyncMock(return_value=existing_post if existing_post is not None else default_post)
    post_repo.update = AsyncMock(side_effect=lambda p: p)

    default_publications = [
        Publication(
            id=uuid4(),
            post_id=post_id,
            account_id=conn_id,
            status=PublicationStatus.PUBLISHED,
        )
    ]

    pub_repo = MagicMock()
    pub_repo.list_by_post = AsyncMock(return_value=publications if publications is not None else default_publications)

    arq_pool = MagicMock()
    arq_pool.enqueue_job = AsyncMock()

    service = EditService(
        post_repo=post_repo,
        publication_repo=pub_repo,
        capability_resolver=CapabilityResolver(),
        arq_pool=arq_pool,
    )

    ctx = TenantContext(tenant_id=tenant_id, tenant_name="TestTenant")
    return service, ctx, post_id, arq_pool


@pytest.mark.asyncio
async def test_edit_post_enqueues_job():
    service, ctx, post_id, arq_pool = make_service()
    new_content = PostContent(title="New Title", body="New body")

    result = await service.edit_post(tenant_ctx=ctx, post_id=post_id, new_content=new_content)

    assert result["post_id"] == str(post_id)
    assert result["enqueued"] is True
    arq_pool.enqueue_job.assert_awaited_once_with("edit_job", str(post_id))


@pytest.mark.asyncio
async def test_edit_post_not_found_raises():
    service, ctx, post_id, _ = make_service(existing_post=None)
    service._post_repo.get_by_id = AsyncMock(return_value=None)
    new_content = PostContent(title="New", body="New body")

    with pytest.raises(PostNotFoundError):
        await service.edit_post(tenant_ctx=ctx, post_id=post_id, new_content=new_content)


@pytest.mark.asyncio
async def test_edit_post_no_published_returns_warning():
    service, ctx, post_id, arq_pool = make_service(publications=[])
    new_content = PostContent(title="New Title", body="New body")

    result = await service.edit_post(tenant_ctx=ctx, post_id=post_id, new_content=new_content)

    assert result["enqueued"] is False
    assert result["warnings"]
    arq_pool.enqueue_job.assert_not_awaited()
