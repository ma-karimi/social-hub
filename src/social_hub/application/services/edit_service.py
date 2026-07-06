from uuid import UUID

from social_hub.application.services.capability_resolver import CapabilityResolver
from social_hub.domain.entities.post import PostContent
from social_hub.domain.exceptions import PostNotFoundError
from social_hub.domain.repositories.post_repo import PostRepository
from social_hub.domain.repositories.publication_repo import PublicationRepository
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.shared.types import TenantContext


class EditService:
    def __init__(
        self,
        post_repo: PostRepository,
        publication_repo: PublicationRepository,
        capability_resolver: CapabilityResolver,
        arq_pool,
    ) -> None:
        self._post_repo = post_repo
        self._publication_repo = publication_repo
        self._capability_resolver = capability_resolver
        self._arq_pool = arq_pool

    async def edit_post(
        self,
        tenant_ctx: TenantContext,
        post_id: UUID,
        new_content: PostContent,
    ) -> dict:
        post = await self._post_repo.get_by_id(tenant_ctx.tenant_id, post_id)
        if post is None:
            raise PostNotFoundError(f"Post {post_id} not found")

        post.content = new_content
        post = await self._post_repo.update(post)

        publications = await self._publication_repo.list_by_post(post_id)
        published = [p for p in publications if p.status == PublicationStatus.PUBLISHED]

        warnings: list[str] = []
        enqueued = 0
        for pub in published:
            await self._arq_pool.enqueue_job("edit_job", str(post_id))
            enqueued += 1
            break  # one job per post_id is enough; edit_job iterates all publications

        if not enqueued and not published:
            warnings.append("No published publications to edit")

        return {
            "post_id": str(post_id),
            "enqueued": enqueued > 0,
            "warnings": warnings,
        }
