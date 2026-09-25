"""
publish_job: loads a Publication, builds OutgoingPost, calls the driver via social account.
"""
from datetime import datetime, timezone
from uuid import UUID

import structlog

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.entities.platform_message import PlatformMessage
from social_hub.domain.entities.post import PostContent
from social_hub.domain.value_objects.media_ref import MediaRef
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.publication_status import PublicationStatus
from social_hub.infrastructure.db.models.post import PostModel
from social_hub.infrastructure.db.models.social_account import SocialAccountModel
from social_hub.infrastructure.db.repositories.button_repo import SQLAlchemyButtonRepo
from social_hub.infrastructure.db.repositories.platform_message_repo import (
    SQLAlchemyPlatformMessageRepo,
)
from social_hub.infrastructure.db.repositories.publication_repo import SQLAlchemyPublicationRepo
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost
from social_hub.infrastructure.platforms.telegram.button_encoder import buttons_to_outgoing

logger = structlog.get_logger(__name__)


async def publish_job(ctx, publication_id: str, connection_id: str) -> None:
    """connection_id is the social_accounts.id (legacy parameter name)."""
    container = ctx["container"]
    pub_id = UUID(publication_id)
    account_id = UUID(connection_id)

    async with container.session_factory() as session:
        async with session.begin():
            pub_repo = SQLAlchemyPublicationRepo(session)
            btn_repo = SQLAlchemyButtonRepo(session)
            msg_repo = SQLAlchemyPlatformMessageRepo(session)

            publication = await pub_repo.get_by_id(pub_id)
            if publication is None:
                logger.error("publish_job_not_found", publication_id=publication_id)
                return

            if publication.status not in (PublicationStatus.PENDING, PublicationStatus.FAILED):
                logger.info("publish_job_skipped", status=publication.status)
                return

            publication.status = PublicationStatus.PROCESSING
            await pub_repo.update(publication)

            post_model = await session.get(PostModel, publication.post_id)
            account_model = await session.get(SocialAccountModel, account_id)

            if post_model is None or account_model is None:
                publication.status = PublicationStatus.FAILED
                publication.error_message = "Post or account not found"
                await pub_repo.update(publication)
                return

            content = PostContent.from_dict(post_model.content or {})
            buttons = await btn_repo.list_by_post(publication.post_id)

            connection = PlatformConnection(
                id=account_model.id,
                tenant_id=account_model.tenant_id,
                platform_type=PlatformType(account_model.platform),
                credentials_encrypted=bytes(account_model.credentials_encrypted or b""),
                settings=account_model.settings or {},
                is_active=account_model.is_active,
            )
            credentials = container.encryptor.decrypt(connection.credentials_encrypted)
            conn_ctx = ConnectionContext(connection=connection, credentials=credentials)

            # Resolve driver from platform type
            from social_hub.infrastructure.platforms.telegram.driver import TelegramDriver
            from social_hub.infrastructure.platforms.bale.driver import BaleDriver
            from social_hub.infrastructure.platforms.eitaa.driver import EitaaDriver

            drivers = {
                PlatformType.TELEGRAM: TelegramDriver(),
                PlatformType.BALE: BaleDriver(),
                PlatformType.EITAA: EitaaDriver(),
            }
            driver = drivers.get(connection.platform_type)
            if driver is None:
                publication.status = PublicationStatus.FAILED
                publication.error_message = "No driver for platform"
                await pub_repo.update(publication)
                return

            media = [MediaRef(url=url, sort_order=i) for i, url in enumerate(content.images)]
            button_rows = buttons_to_outgoing(buttons)
            text = _format_post_text(content, post_model.post_type)
            outgoing = OutgoingPost(text=text, media=media, buttons=button_rows)

            result = await driver.publish(conn_ctx, outgoing)

            if result.success:
                publication.status = PublicationStatus.PUBLISHED
                publication.published_at = datetime.now(timezone.utc)
                await pub_repo.update(publication)
                if result.platform_message_id and result.chat_id:
                    pm = PlatformMessage.create(
                        publication_id=publication.id,
                        platform_message_id=result.platform_message_id,
                        chat_id=result.chat_id,
                    )
                    await msg_repo.create(pm)
            else:
                publication.status = PublicationStatus.FAILED
                publication.error_message = result.error_message
                await pub_repo.update(publication)

    logger.info("publish_job_done", publication_id=publication_id, success=result.success)


def _format_post_text(content: PostContent, post_type: str) -> str:
    parts = []
    if content.title:
        parts.append(f"<b>{content.title}</b>")
    if content.body:
        parts.append(content.body)
    if post_type == "product" and content.price is not None:
        price_str = f"{content.price:,.0f}"
        currency = content.currency or ""
        parts.append(f"\U0001f4b0 {price_str} {currency}".strip())
    return "\n\n".join(parts)
