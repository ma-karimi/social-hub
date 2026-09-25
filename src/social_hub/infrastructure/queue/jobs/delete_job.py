"""delete_job: removes all platform messages for a post and marks publications as deleted."""
from uuid import UUID

import structlog

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.infrastructure.db.models.social_account import SocialAccountModel
from social_hub.infrastructure.db.repositories.platform_message_repo import (
    SQLAlchemyPlatformMessageRepo,
)
from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo
from social_hub.infrastructure.platforms.bale.driver import BaleDriver
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.eitaa.driver import EitaaDriver
from social_hub.infrastructure.platforms.telegram.driver import TelegramDriver

logger = structlog.get_logger(__name__)

_DRIVERS = {
    PlatformType.TELEGRAM: TelegramDriver(),
    PlatformType.BALE: BaleDriver(),
    PlatformType.EITAA: EitaaDriver(),
}


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

                account_model = await session.get(SocialAccountModel, pub.account_id)
                if account_model is None:
                    continue

                messages = await msg_repo.list_by_publication(pub.id)

                platform = PlatformType(account_model.platform)
                connection = PlatformConnection(
                    id=account_model.id,
                    tenant_id=account_model.tenant_id,
                    platform_type=platform,
                    credentials_encrypted=bytes(account_model.credentials_encrypted or b""),
                    settings=account_model.settings or {},
                    is_active=account_model.is_active,
                )
                credentials = container.encryptor.decrypt(connection.credentials_encrypted)
                conn_ctx = ConnectionContext(connection=connection, credentials=credentials)
                driver = _DRIVERS.get(platform)
                if driver is None:
                    continue

                for msg in messages:
                    result = await driver.delete(
                        conn_ctx, msg.platform_message_id, msg.chat_id
                    )
                    if not result.success:
                        logger.error(
                            "delete_failed",
                            publication_id=str(pub.id),
                            error=result.error_message,
                        )

                pub.status = PublicationStatus.DELETED
                await pub_repo.update(pub)

    logger.info("delete_job_done", post_id=post_id)
