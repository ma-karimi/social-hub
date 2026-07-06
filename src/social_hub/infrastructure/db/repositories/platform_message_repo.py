from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.platform_message import PlatformMessage
from social_hub.infrastructure.db.models.platform_message import PlatformMessageModel


def _to_entity(m: PlatformMessageModel) -> PlatformMessage:
    return PlatformMessage(
        id=m.id,
        publication_id=m.publication_id,
        platform_message_id=m.platform_message_id,
        chat_id=m.chat_id,
    )


class SQLAlchemyPlatformMessageRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, message: PlatformMessage) -> PlatformMessage:
        model = PlatformMessageModel(
            id=message.id,
            publication_id=message.publication_id,
            platform_message_id=message.platform_message_id,
            chat_id=message.chat_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def list_by_publication(self, publication_id: UUID) -> list[PlatformMessage]:
        stmt = select(PlatformMessageModel).where(
            PlatformMessageModel.publication_id == publication_id
        )
        results = await self._session.scalars(stmt)
        return [_to_entity(m) for m in results]
