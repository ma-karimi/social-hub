"""edit_job: updates all published platform messages for a post."""
from uuid import UUID

import structlog

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.entities.post import PostContent
from social_hub.domain.value_objects.media_ref import MediaRef
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.infrastructure.db.models.platform_connection import PlatformConnectionModel
from social_hub.infrastructure.db.models.post import PostModel
from social_hub.infrastructure.db.repositories.button_repo import SQLAlchemyButtonRepo
from social_hub.infrastructure.db.repositories.platform_message_repo import (
    SQLAlchemyPlatformMessageRepo,
)
from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost
from social_hub.infrastructure.platforms.telegram.button_encoder import buttons_to_outgoing

logger = structlog.get_logger(__name__)


async def edit_job(ctx, post_id: str) -> None:
    container = ctx["container"]
    pid = UUID(post_id)

    async with container.session_factory() as session:
        async with session.begin():
            pub_repo = SQLAlchemyPublicationRepo(session)
            btn_repo = SQLAlchemyButtonRepo(session)
            msg_repo = SQLAlchemyPlatformMessageRepo(session)

            post_model = await session.get(PostModel, pid)
            if post_model is None:
                logger.error("edit_job_post_not_found", post_id=post_id)
                return

            content = PostContent.from_dict(post_model.content or {})
            buttons = await btn_repo.list_by_post(pid)
            publications = await pub_repo.list_by_post(pid)

            for pub in publications:
                if pub.status != PublicationStatus.PUBLISHED:
                    continue

                conn_model = await session.get(PlatformConnectionModel, pub.connection_id)
                if conn_model is None:
                    continue

                messages = await msg_repo.list_by_publication(pub.id)
                if not messages:
                    continue

                connection = PlatformConnection(
                    id=conn_model.id,
                    tenant_id=conn_model.tenant_id,
                    platform_type=PlatformType(conn_model.platform_type),
                    credentials_encrypted=bytes(conn_model.credentials_encrypted),
                    settings=conn_model.settings or {},
                    is_active=conn_model.is_active,
                )
                credentials = container.encryptor.decrypt(connection.credentials_encrypted)
                conn_ctx = ConnectionContext(connection=connection, credentials=credentials)
                driver = container.driver_registry.get(connection.platform_type)

                caps = container.capability_resolver.resolve(connection.platform_type)
                if not caps.can_edit:
                    logger.info("edit_skipped_no_capability", platform=connection.platform_type)
                    continue

                media = [MediaRef(url=u, sort_order=i) for i, u in enumerate(content.images)]
                button_rows = buttons_to_outgoing(buttons)
                from social_hub.infrastructure.queue.jobs.publish_job import _format_post_text
                text = _format_post_text(content, post_model.post_type)
                outgoing = OutgoingPost(text=text, media=media, buttons=button_rows)

                for msg in messages:
                    result = await driver.edit(
                        conn_ctx,
                        platform_message_id=msg.platform_message_id,
                        chat_id=msg.chat_id,
                        outgoing=outgoing,
                    )
                    if not result.success:
                        logger.warning(
                            "edit_job_failed",
                            message_id=msg.platform_message_id,
                            error=result.error_message,
                        )

    logger.info("edit_job_done", post_id=post_id)
