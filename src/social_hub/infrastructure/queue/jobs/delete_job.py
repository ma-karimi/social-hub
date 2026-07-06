"""delete_job: removes all platform messages for a post and marks publications as deleted."""
from uuid import UUID

import structlog

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.infrastructure.db.models.platform_connection import PlatformConnectionModel
from social_hub.infrastructure.db.repositories.platform_message_repo import (
    SQLAlchemyPlatformMessageRepo,
)
from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo
from social_hub.infrastructure.platforms.base import ConnectionContext

logger = structlog.get_logger(__name__)


async def delete_job(ctx, post_id: str) -> None:
    container = ctx["container"]
    pid = UUID(post_id)

    async with container.session_factory() as session:
        async with session.begin():
            pub_repo = SQLAlchemyPublicationRepo(session)
            msg_repo = SQLAlchemyPlatformMessageRepo(session)

            publications = await pub_repo.list_by_post(pid)

            for pub in publications:
                if pub.status != PublicationStatus.PUBLISHED:
                    continue

                conn_model = await session.get(PlatformConnectionModel, pub.connection_id)
                if conn_model is None:
                    continue

                messages = await msg_repo.list_by_publication(pub.id)

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
                if not caps.can_delete:
                    logger.info("delete_skipped_no_capability", platform=connection.platform_type)
                    pub.status = PublicationStatus.DELETED
                    await pub_repo.update(pub)
                    continue

                all_deleted = True
                for msg in messages:
                    result = await driver.delete(
                        conn_ctx,
                        platform_message_id=msg.platform_message_id,
                        chat_id=msg.chat_id,
                    )
                    if not result.success:
                        all_deleted = False
                        logger.warning(
                            "delete_job_msg_failed",
                            message_id=msg.platform_message_id,
                            error=result.error_message,
                        )

                if all_deleted:
                    pub.status = PublicationStatus.DELETED
                    await pub_repo.update(pub)

    logger.info("delete_job_done", post_id=post_id)
