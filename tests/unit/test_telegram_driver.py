import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

pytest.importorskip("structlog", reason="structlog not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.dto.outgoing_button import OutgoingButton
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost
from social_hub.infrastructure.platforms.telegram.driver import TelegramDriver


def make_ctx():
    connection = PlatformConnection(
        id=uuid4(),
        tenant_id=uuid4(),
        platform_type=PlatformType.TELEGRAM,
        credentials_encrypted=b"",
        settings={"channel_id": "@test_channel"},
    )
    return ConnectionContext(connection=connection, credentials={"bot_token": "test:token"})


@pytest.mark.asyncio
async def test_publish_text_only():
    driver = TelegramDriver()
    ctx = make_ctx()
    outgoing = OutgoingPost(text="Hello!")

    mock_result = {"message_id": 55, "chat": {"id": -100123}}

    with patch(
        "social_hub.infrastructure.platforms.telegram.driver.TelegramClient.send_message",
        new=AsyncMock(return_value=mock_result),
    ):
        result = await driver.publish(ctx, outgoing)

    assert result.success is True
    assert result.platform_message_id == "55"
    assert result.chat_id == "-100123"


@pytest.mark.asyncio
async def test_publish_returns_failure_on_api_error():
    driver = TelegramDriver()
    ctx = make_ctx()
    outgoing = OutgoingPost(text="Hello!")

    from social_hub.infrastructure.platforms.telegram.client import TelegramAPIError
    with patch(
        "social_hub.infrastructure.platforms.telegram.driver.TelegramClient.send_message",
        new=AsyncMock(side_effect=TelegramAPIError("Bot blocked", 403)),
    ):
        result = await driver.publish(ctx, outgoing)

    assert result.success is False
    assert "Bot blocked" in (result.error_message or "")


def test_verify_webhook_no_secret_always_true():
    driver = TelegramDriver()
    assert driver.verify_webhook({}, b"body", secret=None) is True


def test_verify_webhook_correct_secret():
    driver = TelegramDriver()
    headers = {"x-telegram-bot-api-secret-token": "mysecret"}
    assert driver.verify_webhook(headers, b"body", secret="mysecret") is True


def test_verify_webhook_wrong_secret():
    driver = TelegramDriver()
    headers = {"x-telegram-bot-api-secret-token": "wrongsecret"}
    assert driver.verify_webhook(headers, b"body", secret="mysecret") is False
