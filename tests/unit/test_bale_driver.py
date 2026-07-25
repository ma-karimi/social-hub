import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

pytest.importorskip("structlog", reason="structlog not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost
from social_hub.infrastructure.platforms.bale.driver import BaleDriver
from social_hub.domain.value_objects.media_ref import MediaRef


def make_ctx():
    connection = PlatformConnection(
        id=uuid4(),
        tenant_id=uuid4(),
        platform_type=PlatformType.BALE,
        credentials_encrypted=b"",
        settings={"channel_id": "@test_bale_channel"},
    )
    return ConnectionContext(connection=connection, credentials={"bot_token": "test:token"})


@pytest.mark.asyncio
async def test_publish_text_only():
    driver = BaleDriver()
    ctx = make_ctx()
    outgoing = OutgoingPost(text="سلام بله!")

    mock_result = {"message_id": 77, "chat": {"id": -100999}}

    with patch(
        "social_hub.infrastructure.platforms.bale.driver.BaleClient.send_message",
        new=AsyncMock(return_value=mock_result),
    ):
        result = await driver.publish(ctx, outgoing)

    assert result.success is True
    assert result.platform_message_id == "77"
    assert result.chat_id == "-100999"


@pytest.mark.asyncio
async def test_publish_uses_first_image_only():
    driver = BaleDriver()
    ctx = make_ctx()
    outgoing = OutgoingPost(
        text="کپشن",
        media=[
            MediaRef(url="https://example.com/a.jpg", sort_order=0),
            MediaRef(url="https://example.com/b.jpg", sort_order=1),
        ],
    )

    mock_result = {"message_id": 88, "chat": {"id": -100999}}
    send_photo = AsyncMock(return_value=mock_result)

    with patch(
        "social_hub.infrastructure.platforms.bale.driver.BaleClient.send_photo",
        new=send_photo,
    ):
        result = await driver.publish(ctx, outgoing)

    assert result.success is True
    send_photo.assert_awaited_once()
    assert send_photo.await_args.kwargs["photo"] == "https://example.com/a.jpg"


@pytest.mark.asyncio
async def test_publish_returns_failure_on_api_error():
    driver = BaleDriver()
    ctx = make_ctx()
    outgoing = OutgoingPost(text="Hello!")

    from social_hub.infrastructure.platforms.bale.client import BaleAPIError

    with patch(
        "social_hub.infrastructure.platforms.bale.driver.BaleClient.send_message",
        new=AsyncMock(side_effect=BaleAPIError("Forbidden", 403)),
    ):
        result = await driver.publish(ctx, outgoing)

    assert result.success is False
    assert "Forbidden" in (result.error_message or "")


def test_verify_webhook_no_secret_always_true():
    driver = BaleDriver()
    assert driver.verify_webhook({}, b"body", secret=None) is True


def test_verify_webhook_correct_secret():
    driver = BaleDriver()
    headers = {"x-webhook-secret": "mysecret"}
    assert driver.verify_webhook(headers, b"body", secret="mysecret") is True


def test_verify_webhook_wrong_secret():
    driver = BaleDriver()
    headers = {"x-webhook-secret": "wrongsecret"}
    assert driver.verify_webhook(headers, b"body", secret="mysecret") is False
