from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from social_hub.domain.entities.interaction_event import InteractionEvent, ReplyContext
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.button_action import ButtonAction
from social_hub.infrastructure.db.models.interaction_event import InteractionEventModel


def _to_entity(m: InteractionEventModel) -> InteractionEvent:
    reply_context = None
    if m.reply_context:
        reply_context = ReplyContext(
            chat_id=m.reply_context.get("chat_id", ""),
            message_id=m.reply_context.get("message_id"),
            callback_query_id=m.reply_context.get("callback_query_id"),
            extra=m.reply_context.get("extra", {}),
        )
    return InteractionEvent(
        id=m.id,
        tenant_id=m.tenant_id,
        button_id=m.button_id,
        platform_type=PlatformType(m.platform_type),
        action=ButtonAction(m.action) if m.action else None,
        payload=m.payload or {},
        user_platform_id=m.user_platform_id,
        raw_payload=m.raw_payload or {},
        reply_context=reply_context,
        status=m.status,
        processed_at=m.processed_at,
        created_at=m.created_at,
    )


def _reply_context_to_dict(rc: ReplyContext | None) -> dict:
    if rc is None:
        return {}
    return {
        "chat_id": rc.chat_id,
        "message_id": rc.message_id,
        "callback_query_id": rc.callback_query_id,
        "extra": rc.extra,
    }


class SQLAlchemyInteractionEventRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: InteractionEvent) -> InteractionEvent:
        model = InteractionEventModel(
            id=event.id,
            tenant_id=event.tenant_id,
            button_id=event.button_id,
            platform_type=event.platform_type,
            action=event.action,
            payload=event.payload,
            user_platform_id=event.user_platform_id,
            raw_payload=event.raw_payload,
            reply_context=_reply_context_to_dict(event.reply_context),
            status=event.status,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, event_id: UUID) -> InteractionEvent | None:
        result = await self._session.get(InteractionEventModel, event_id)
        return _to_entity(result) if result else None

    async def update(self, event: InteractionEvent) -> InteractionEvent:
        model = await self._session.get(InteractionEventModel, event.id)
        if model is None:
            raise ValueError(f"InteractionEvent {event.id} not found")
        model.status = event.status
        model.processed_at = event.processed_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
