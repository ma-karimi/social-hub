from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.button import Button
from social_hub.domain.value_objects.button_action import ButtonAction
from social_hub.infrastructure.db.models.button import ButtonModel
from social_hub.shared.utils import encode_short_id


def _to_entity(m: ButtonModel) -> Button:
    return Button(
        id=m.id,
        post_id=m.post_id,
        action_type=ButtonAction(m.action_type),
        label=m.label,
        payload=m.payload or {},
        sort_order=m.sort_order,
        short_id=m.short_id,
    )


class SQLAlchemyButtonRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, buttons: list[Button]) -> list[Button]:
        models = []
        for btn in buttons:
            short_id = encode_short_id(btn.id)
            model = ButtonModel(
                id=btn.id,
                post_id=btn.post_id,
                action_type=btn.action_type,
                label=btn.label,
                payload=btn.payload,
                sort_order=btn.sort_order,
                short_id=short_id,
            )
            self._session.add(model)
            models.append(model)
        await self._session.flush()
        for m in models:
            await self._session.refresh(m)
        return [_to_entity(m) for m in models]

    async def list_by_post(self, post_id: UUID) -> list[Button]:
        stmt = (
            select(ButtonModel)
            .where(ButtonModel.post_id == post_id)
            .order_by(ButtonModel.sort_order)
        )
        results = await self._session.scalars(stmt)
        return [_to_entity(m) for m in results]

    async def get_by_short_id(self, short_id: str) -> Button | None:
        stmt = select(ButtonModel).where(ButtonModel.short_id == short_id)
        result = await self._session.scalar(stmt)
        return _to_entity(result) if result else None

    async def update_short_ids(self, buttons: list[Button]) -> None:
        for btn in buttons:
            if btn.short_id:
                model = await self._session.get(ButtonModel, btn.id)
                if model:
                    model.short_id = btn.short_id
        await self._session.flush()
