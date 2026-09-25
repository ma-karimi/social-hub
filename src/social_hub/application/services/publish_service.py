from uuid import UUID

from social_hub.domain.entities.button import Button
from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.entities.publication import Publication
from social_hub.domain.exceptions import ConnectionNotFoundError, DuplicatePostError
from social_hub.domain.repositories.button_repo import ButtonRepository
from social_hub.domain.repositories.connection_repo import ConnectionRepository
from social_hub.domain.repositories.post_repo import PostRepository
from social_hub.domain.repositories.publication_repo import PublicationRepository
from social_hub.domain.value_objects.button_action import ButtonAction
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.post_type import PostType
from social_hub.application.services.capability_resolver import CapabilityResolver
from social_hub.shared.types import TenantContext


class PublishService:
    def __init__(
        self,
        post_repo: PostRepository,
        connection_repo: ConnectionRepository,
        publication_repo: PublicationRepository,
        button_repo: ButtonRepository,
        capability_resolver: CapabilityResolver,
        arq_pool,
    ) -> None:
        self._post_repo = post_repo
        self._connection_repo = connection_repo
        self._publication_repo = publication_repo
        self._button_repo = button_repo
        self._capability_resolver = capability_resolver
        self._arq_pool = arq_pool

    async def publish_product(
        self,
        tenant_ctx: TenantContext,
        platforms: list[PlatformType],
        content: PostContent,
        buttons_data: list[dict],
        external_ref: str | None = None,
    ) -> dict:
        return await self._publish(
            tenant_ctx=tenant_ctx,
            post_type=PostType.PRODUCT,
            platforms=platforms,
            content=content,
            buttons_data=buttons_data,
            external_ref=external_ref,
        )

    async def publish_normal(
        self,
        tenant_ctx: TenantContext,
        platforms: list[PlatformType],
        content: PostContent,
        external_ref: str | None = None,
    ) -> dict:
        return await self._publish(
            tenant_ctx=tenant_ctx,
            post_type=PostType.NORMAL,
            platforms=platforms,
            content=content,
            buttons_data=[],
            external_ref=external_ref,
        )

    async def _publish(
        self,
        tenant_ctx: TenantContext,
        post_type: PostType,
        platforms: list[PlatformType],
        content: PostContent,
        buttons_data: list[dict],
        external_ref: str | None,
    ) -> dict:
        if external_ref:
            existing = await self._post_repo.get_by_external_ref(
                tenant_ctx.tenant_id, external_ref
            )
            if existing:
                raise DuplicatePostError(
                    f"Post with external_ref='{external_ref}' already exists"
                )

        connections = {}
        for platform in platforms:
            conn = await self._connection_repo.get_by_platform(tenant_ctx.tenant_id, platform)
            if conn is None or not conn.is_active:
                raise ConnectionNotFoundError(
                    f"No active connection for platform '{platform}'"
                )
            connections[platform] = conn

        post = Post.create(
            tenant_id=tenant_ctx.tenant_id,
            post_type=post_type,
            content=content,
            external_ref=external_ref,
        )
        post = await self._post_repo.create(post)

        buttons: list[Button] = []
        for i, btn_data in enumerate(buttons_data):
            btn = Button.create(
                post_id=post.id,
                action_type=ButtonAction(btn_data["action"]),
                label=btn_data["label"],
                payload=btn_data.get("payload", {}),
                sort_order=i,
            )
            buttons.append(btn)
        if buttons:
            buttons = await self._button_repo.create_many(buttons)

        publications = []
        warnings = []
        for platform, conn in connections.items():
            caps = self._capability_resolver.resolve(platform)

            if not caps.can_publish:
                warnings.append(f"{platform}: publishing not supported, skipped")
                continue

            if buttons and not caps.supports_buttons:
                warnings.append(f"{platform}: buttons not supported and will be stripped")

            pub = Publication.create(post_id=post.id, account_id=conn.id)
            pub = await self._publication_repo.create(pub)
            publications.append(pub)

            await self._arq_pool.enqueue_job(
                "publish_job",
                str(pub.id),
                str(conn.id),
            )

        return {
            "post_id": str(post.id),
            "publications": [
                {
                    "id": str(p.id),
                    "status": p.status,
                    "connection_id": str(p.account_id),
                    "account_id": str(p.account_id),
                }
                for p in publications
            ],
            "warnings": warnings,
        }
