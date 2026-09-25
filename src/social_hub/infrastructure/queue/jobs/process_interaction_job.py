"""process_interaction_job: handles incoming platform callbacks from the webhook."""
from uuid import UUID

import structlog

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.db.repositories.button_repo import SQLAlchemyButtonRepo
from social_hub.infrastructure.db.repositories.interaction_event_repo import (
    SQLAlchemyInteractionEventRepo,
)
from social_hub.infrastructure.db.repositories.tenant_repo import SQLAlchemyTenantRepo
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.dto.incoming_event import IncomingEvent, IncomingEventType

logger = structlog.get_logger(__name__)


async def process_interaction_job(ctx, payload: dict) -> None:
    container = ctx["container"]

    incoming = IncomingEvent(
        event_type=IncomingEventType(payload["incoming"]["event_type"]),
        user_ref=payload["incoming"]["user_ref"],
        raw=payload["incoming"]["raw"],
        button_short_id=payload["incoming"].get("button_short_id"),
        reply_chat_id=payload["incoming"].get("reply_chat_id"),
        reply_message_id=payload["incoming"].get("reply_message_id"),
        callback_query_id=payload["incoming"].get("callback_query_id"),
    )

    connection = PlatformConnection(
        id=UUID(payload["connection_id"]),
        tenant_id=UUID(payload["tenant_id"]),
        platform_type=PlatformType(payload["platform_type"]),
        credentials_encrypted=b"",  # not needed; credentials passed directly
        settings=payload.get("connection_settings", {}),
        is_active=True,
    )
    conn_ctx = ConnectionContext(
        connection=connection,
        credentials=payload["credentials"],
    )

    async with container.session_factory() as session:
        async with session.begin():
            from social_hub.application.services.interaction_service import InteractionService
            service = InteractionService(
                tenant_repo=SQLAlchemyTenantRepo(session),
                button_repo=SQLAlchemyButtonRepo(session),
                interaction_event_repo=SQLAlchemyInteractionEventRepo(session),
            )
            await service.handle(incoming=incoming, connection_ctx=conn_ctx)

    logger.info(
        "process_interaction_done",
        tenant_id=payload["tenant_id"],
        event_type=payload["incoming"]["event_type"],
    )
