from uuid import UUID

from social_hub.domain.exceptions import PostNotFoundError
from social_hub.domain.repositories.post_repo import PostRepository
from social_hub.domain.repositories.publication_repo import PublicationRepository
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.shared.types import TenantContext


class DeleteService:
    def __init__(
        self,
        post_repo: PostRepository,
        publication_repo: PublicationRepository,
        arq_pool,
    ) -> None:
        self._post_repo = post_repo
        self._publication_repo = publication_repo
        self._arq_pool = arq_pool

    async def delete_post(
        self,
        tenant_ctx: TenantContext,
        post_id: UUID,
    ) -> dict:
        post = await self._post_repo.get_by_id(tenant_ctx.tenant_id, post_id)
        if post is None:
            raise PostNotFoundError(f"Post {post_id} not found")

        publications = await self._publication_repo.list_by_post(post_id)
        published = [p for p in publications if p.status == PublicationStatus.PUBLISHED]

        if published:
            await self._arq_pool.enqueue_job("delete_job", str(post_id))

        return {
            "post_id": str(post_id),
            "delete_enqueued": len(published),
        }
