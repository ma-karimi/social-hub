from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.publication import Publication
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.infrastructure.db.models.publication import PublicationModel


def _to_entity(m: PublicationModel) -> Publication:
    return Publication(
        id=m.id,
        post_id=m.post_id,
        connection_id=m.connection_id,
        status=PublicationStatus(m.status),
        error_message=m.error_message,
        platform_metadata=m.platform_metadata or {},
        published_at=m.published_at,
        created_at=m.created_at,
    )


class SQLAlchemyPublicationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, publication: Publication) -> Publication:
        model = PublicationModel(
            id=publication.id,
            post_id=publication.post_id,
            connection_id=publication.connection_id,
            status=publication.status,
            error_message=publication.error_message,
            platform_metadata=publication.platform_metadata,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, publication_id: UUID) -> Publication | None:
        result = await self._session.get(PublicationModel, publication_id)
        return _to_entity(result) if result else None

    async def list_by_post(self, post_id: UUID) -> list[Publication]:
        stmt = select(PublicationModel).where(PublicationModel.post_id == post_id)
        results = await self._session.scalars(stmt)
        return [_to_entity(m) for m in results]

    async def update(self, publication: Publication) -> Publication:
        model = await self._session.get(PublicationModel, publication.id)
        if model is None:
            raise ValueError(f"Publication {publication.id} not found")
        model.status = publication.status
        model.error_message = publication.error_message
        model.platform_metadata = publication.platform_metadata
        model.published_at = publication.published_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_post_and_connection(
        self, post_id: UUID, connection_id: UUID
    ) -> Publication | None:
        stmt = select(PublicationModel).where(
            PublicationModel.post_id == post_id,
            PublicationModel.connection_id == connection_id,
        )
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None
