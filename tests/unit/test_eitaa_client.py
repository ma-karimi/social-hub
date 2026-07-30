import pytest

pytest.importorskip("httpx", reason="httpx not installed")

from social_hub.infrastructure.platforms.eitaa.client import EitaaClient


def test_normalize_chat_id_strips_at():
    assert EitaaClient._normalize_chat_id("@mychannel") == "mychannel"
    assert EitaaClient._normalize_chat_id("mychannel") == "mychannel"
    assert EitaaClient._normalize_chat_id("1404") == "1404"


def test_filename_from_url():
    assert EitaaClient._filename_from_url("https://cdn.example.com/a/b.jpg", None) == "b.jpg"
    assert (
        EitaaClient._filename_from_url("https://cdn.example.com/x", "image/png") == "file.png"
    )
