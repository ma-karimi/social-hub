from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.value_objects.post_type import PostType
from social_hub.infrastructure.db.models.post import PostModel


def _to_entity(m: PostModel) -> Post:
    return Post(
        id=m.id,
        tenant_id=m.tenant_id,
        post_type=PostType(m.post_type),
        content=PostContent.from_dict(m.content or {}),
        status=m.status,
        external_ref=m.external_ref,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyPostRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, post: Post) -> Post:
        model = PostModel(
            id=post.id,
            tenant_id=post.tenant_id,
            post_type=post.post_type,
            content=post.content.to_dict(),
            status=post.status,
            external_ref=post.external_ref,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, tenant_id: UUID, post_id: UUID) -> Post | None:
        stmt = select(PostModel).where(
            PostModel.id == post_id,
            PostModel.tenant_id == tenant_id,
        )
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None

    async def get_by_external_ref(self, tenant_id: UUID, external_ref: str) -> Post | None:
        stmt = select(PostModel).where(
            PostModel.tenant_id == tenant_id,
            PostModel.external_ref == external_ref,
        )
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None

    async def update(self, post: Post) -> Post:
        model = await self._session.get(PostModel, post.id)
        if model is None:
            raise ValueError(f"Post {post.id} not found")
        model.content = post.content.to_dict()
        model.status = post.status
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_by_tenant(
        self, tenant_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Post]:
        stmt = (
            select(PostModel)
            .where(PostModel.tenant_id == tenant_id)
            .order_by(PostModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        results = await self._session.scalars(stmt)
        return [_to_entity(m) for m in results]
