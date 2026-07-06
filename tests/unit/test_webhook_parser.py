from social_hub.infrastructure.platforms.telegram.webhook_parser import parse_update
from social_hub.infrastructure.platforms.dto.incoming_event import IncomingEventType


CALLBACK_UPDATE = {
    "update_id": 100,
    "callback_query": {
        "id": "cq123",
        "from": {"id": 42, "first_name": "Ali"},
        "message": {
            "message_id": 7,
            "chat": {"id": -100123456, "type": "channel"},
        },
        "data": "sh:abc12345",
    },
}

UNKNOWN_UPDATE = {"update_id": 200, "channel_post": {"text": "hello"}}


def test_parse_callback_query():
    event = parse_update(CALLBACK_UPDATE)
    assert event is not None
    assert event.event_type == IncomingEventType.CALLBACK
    assert event.user_ref == "42"
    assert event.button_short_id == "abc12345"
    assert event.reply_chat_id == "-100123456"
    assert event.reply_message_id == "7"
    assert event.callback_query_id == "cq123"


def test_parse_unknown_update_returns_none():
    assert parse_update(UNKNOWN_UPDATE) is None


def test_parse_non_sh_callback_data():
    update = {
        "update_id": 101,
        "callback_query": {
            "id": "cq456",
            "from": {"id": 99},
            "message": {"message_id": 1, "chat": {"id": -1}},
            "data": "some_other_data",
        },
    }
    event = parse_update(update)
    assert event is not None
    assert event.button_short_id is None
