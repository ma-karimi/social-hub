import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

pytest.importorskip("structlog", reason="structlog not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.value_objects.media_ref import MediaRef
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.base import ConnectionContext
from social_hub.infrastructure.platforms.dto.outgoing_post import OutgoingPost
from social_hub.infrastructure.platforms.eitaa.driver import EitaaDriver


def make_ctx(**settings_overrides):
    settings = {"channel_id": "@test_eitaa_channel", **settings_overrides}
    connection = PlatformConnection(
        id=uuid4(),
        tenant_id=uuid4(),
        platform_type=PlatformType.EITAA,
        credentials_encrypted=b"",
        settings=settings,
    )
    return ConnectionContext(
        connection=connection,
        credentials={"bot_token": "bot511500:test-token"},
    )


@pytest.mark.asyncio
async def test_publish_text_only():
    driver = EitaaDriver()
    ctx = make_ctx()
    outgoing = OutgoingPost(text="سلام ایتا!")

    mock_result = {"message_id": 91, "chat": {"id": 1404}}

    with patch(
        "social_hub.infrastructure.platforms.eitaa.driver.EitaaClient.send_message",
        new=AsyncMock(return_value=mock_result),
    ) as send_message:
        result = await driver.publish(ctx, outgoing)

    assert result.success is True
    assert result.platform_message_id == "91"
    assert result.chat_id == "1404"
    send_message.assert_awaited_once()
    assert send_message.await_args.kwargs["chat_id"] == "@test_eitaa_channel"
    assert send_message.await_args.kwargs["text"] == "سلام ایتا!"


@pytest.mark.asyncio
async def test_publish_uses_first_file_only():
    driver = EitaaDriver()
    ctx = make_ctx(pin=True, title="محصول")
    outgoing = OutgoingPost(
        text="کپشن",
        media=[
            MediaRef(url="https://example.com/a.jpg", sort_order=0),
            MediaRef(url="https://example.com/b.jpg", sort_order=1),
        ],
    )

    mock_result = {"message_id": 92, "chat": {"id": 1404}}
    send_file = AsyncMock(return_value=mock_result)

    with patch(
        "social_hub.infrastructure.platforms.eitaa.driver.EitaaClient.send_file_from_url",
        new=send_file,
    ):
        result = await driver.publish(ctx, outgoing)

    assert result.success is True
    send_file.assert_awaited_once()
    assert send_file.await_args.kwargs["url"] == "https://example.com/a.jpg"
    assert send_file.await_args.kwargs["caption"] == "کپشن"
    assert send_file.await_args.kwargs["pin"] is True
    assert send_file.await_args.kwargs["title"] == "محصول"


@pytest.mark.asyncio
async def test_publish_returns_failure_on_api_error():
    driver = EitaaDriver()
    ctx = make_ctx()
    outgoing = OutgoingPost(text="Hello!")

    from social_hub.infrastructure.platforms.eitaa.client import EitaaAPIError

    with patch(
        "social_hub.infrastructure.platforms.eitaa.driver.EitaaClient.send_message",
        new=AsyncMock(side_effect=EitaaAPIError("Invalid chat_id", 400)),
    ):
        result = await driver.publish(ctx, outgoing)

    assert result.success is False
    assert "Invalid chat_id" in (result.error_message or "")


@pytest.mark.asyncio
async def test_edit_not_supported():
    driver = EitaaDriver()
    ctx = make_ctx()
    result = await driver.edit(ctx, "1", "1404", OutgoingPost(text="x"))
    assert result.success is False
    assert "does not support editing" in (result.error_message or "")


@pytest.mark.asyncio
async def test_delete_not_supported():
    driver = EitaaDriver()
    ctx = make_ctx()
    result = await driver.delete(ctx, "1", "1404")
    assert result.success is False
    assert "does not support deleting" in (result.error_message or "")


def test_parse_incoming_always_none():
    driver = EitaaDriver()
    assert driver.parse_incoming({"update_id": 1}) is None


def test_verify_webhook_only_when_no_secret():
    driver = EitaaDriver()
    assert driver.verify_webhook({}, b"body", secret=None) is True
    assert driver.verify_webhook({}, b"body", secret="x") is False
