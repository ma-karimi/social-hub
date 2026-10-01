from uuid import UUID

from social_hub.application.adapters.base import CreatePostRequest, MediaItem, SocialPostResult
from social_hub.application.adapters.registry import PlatformAdapterRegistry
from social_hub.domain.entities.button import Button
from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.entities.publication import Publication
from social_hub.domain.exceptions import AccountNotFoundError, DuplicatePostError, PostNotFoundError
from social_hub.domain.value_objects.button_action import ButtonAction
from social_hub.domain.value_objects.post_type import PostType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.infrastructure.db.repositories.button_repo import SQLAlchemyButtonRepo
from social_hub.infrastructure.db.repositories.post_repo import SQLAlchemyPostRepo
from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo
from social_hub.infrastructure.db.repositories.social_account_repo import (
    SQLAlchemySocialAccountRepo,
)
from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor
from social_hub.shared.types import TenantContext


class SocialPostService:
    def __init__(
        self,
        post_repo: SQLAlchemyPostRepo,
        account_repo: SQLAlchemySocialAccountRepo,
        publication_repo: SQLAlchemyPublicationRepo,
        button_repo: SQLAlchemyButtonRepo,
        adapter_registry: PlatformAdapterRegistry,
        encryptor: FernetEncryptor,
        arq_pool=None,
    ) -> None:
        self._posts = post_repo
        self._accounts = account_repo
        self._pubs = publication_repo
        self._buttons = button_repo
        self._adapters = adapter_registry
        self._encryptor = encryptor
        self._arq = arq_pool

    async def create_post(
        self,
        tenant_ctx: TenantContext,
        *,
        account_ids: list[UUID],
        content: str | None = None,
        title: str | None = None,
        media_items: list[dict] | None = None,
        publish_now: bool = False,
        scheduled_for: str | None = None,
        is_draft: bool = False,
        timezone: str = "Asia/Tehran",
        platform_specific_data: dict | None = None,
        metadata: dict | None = None,
        external_ref: str | None = None,
        price: float | None = None,
        currency: str | None = None,
        buttons: list[dict] | None = None,
        request_id: str | None = None,
    ) -> SocialPostResult:
        if external_ref:
            existing = await self._posts.get_by_external_ref(tenant_ctx.tenant_id, external_ref)
            if existing:
                raise DuplicatePostError(
                    f"Post with external_ref='{external_ref}' already exists"
                )

        accounts = []
        for aid in account_ids:
            acc = await self._accounts.get_by_id(tenant_ctx.tenant_id, aid)
            if acc is None or not acc.is_active:
                raise AccountNotFoundError(f"Account {aid} not found")
            accounts.append(acc)

        media = media_items or []
        images = [m["url"] for m in media if (m.get("type") or "image") == "image"]
        post_content = PostContent(
            title=title or "",
            body=content or "",
            price=price,
            currency=currency,
            images=images,
            metadata={
                **(metadata or {}),
                "media_items": media,
                "platform_specific_data": platform_specific_data or {},
                "timezone": timezone,
                "scheduled_for": scheduled_for,
                "publish_now": publish_now,
                "is_draft": is_draft,
            },
        )
        post_type = PostType.PRODUCT if price is not None else PostType.NORMAL
        post = Post.create(
            tenant_id=tenant_ctx.tenant_id,
            post_type=post_type,
            content=post_content,
            external_ref=external_ref,
        )
        if publish_now and not is_draft:
            post.status = "publishing"
        elif scheduled_for and not is_draft:
            post.status = "scheduled"
        else:
            post.status = "draft"
        post = await self._posts.create(post)

        button_entities: list[Button] = []
        for i, b in enumerate(buttons or []):
            btn = Button.create(
                post_id=post.id,
                action_type=ButtonAction(b.get("action", "callback")),
                label=b.get("label", ""),
                payload=b.get("payload") or {},
                sort_order=i,
            )
            if b.get("short_id"):
                btn.short_id = b["short_id"]
            button_entities.append(btn)
        if button_entities:
            await self._buttons.create_many(button_entities)

        req = CreatePostRequest(
            content=content,
            title=title,
            media_items=[
                MediaItem(url=m["url"], type=m.get("type")) for m in media
            ],
            account_ids=account_ids,
            publish_now=publish_now,
            scheduled_for=scheduled_for,
            is_draft=is_draft,
            timezone=timezone or "Asia/Tehran",
            platform_specific_data=platform_specific_data or {},
            metadata=metadata or {},
            external_ref=external_ref,
            price=price,
            currency=currency,
            buttons=buttons or [],
            request_id=request_id,
        )

        platform_results = []
        for account in accounts:
            adapter = self._adapters.get(account.platform)
            creds = None
            if account.credentials_encrypted:
                creds = self._encryptor.decrypt(account.credentials_encrypted)

            pub = Publication.create(post_id=post.id, account_id=account.id)
            pub = await self._pubs.create(pub)

            # Instagram (and sync platforms): publish immediately via adapter
            # Bot platforms: also sync via adapter for unified path (no separate job required)
            result = await adapter.create_post(tenant_ctx, account, req, credentials=creds)
            if result.status in ("published", "scheduled", "draft"):
                pub.status = (
                    PublicationStatus.PUBLISHED
                    if result.status == "published"
                    else PublicationStatus.PENDING
                )
                await self._pubs.update(pub)
            else:
                pub.status = PublicationStatus.FAILED
                pub.error_message = result.error
                await self._pubs.update(pub)
            platform_results.append(result)

        statuses = {r.status for r in platform_results}
        if statuses == {"failed"}:
            http_status = 207
            overall = "failed"
        elif "failed" in statuses and len(statuses) > 1:
            http_status = 207
            overall = "partial"
        elif request_id and any(r.platform_message_id for r in platform_results):
            http_status = 201
            overall = platform_results[0].status if platform_results else "created"
        else:
            http_status = 201
            overall = platform_results[0].status if platform_results else post.status

        post.status = overall if overall != "partial" else "published"
        await self._posts.update(post)

        return SocialPostResult(
            post_id=post.id,
            status=overall,
            http_status=http_status,
            platforms=platform_results,
        )

    async def get_post(self, tenant_ctx: TenantContext, post_id: UUID) -> dict:
        post = await self._posts.get_by_id(tenant_ctx.tenant_id, post_id)
        if post is None:
            raise PostNotFoundError()
        pubs = await self._pubs.list_by_post(post.id)
        return {
            "id": str(post.id),
            "tenant_id": str(post.tenant_id),
            "post_type": post.post_type,
            "status": post.status,
            "external_ref": post.external_ref,
            "content": post.content.body if hasattr(post.content, "body") else None,
            "publications": [
                {
                    "id": str(p.id),
                    "status": str(p.status),
                    "account_id": str(p.account_id),
                    "error": p.error_message,
                }
                for p in pubs
            ],
        }

    async def list_posts(
        self, tenant_ctx: TenantContext, *, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        posts = await self._posts.list_by_tenant(
            tenant_ctx.tenant_id, limit=limit, offset=offset
        )
        return [
            {
                "id": str(p.id),
                "tenant_id": str(p.tenant_id),
                "post_type": p.post_type,
                "status": p.status,
                "external_ref": p.external_ref,
            }
            for p in posts
        ]

    async def delete_post(self, tenant_ctx: TenantContext, post_id: UUID) -> None:
        post = await self._posts.get_by_id(tenant_ctx.tenant_id, post_id)
        if post is None:
            raise PostNotFoundError()
        await self._posts.delete(tenant_ctx.tenant_id, post_id)
