import uuid
from social_hub.infrastructure.platforms.telegram.button_encoder import (
    make_callback_data,
    parse_callback_data,
    buttons_to_outgoing,
    CALLBACK_PREFIX,
)
from social_hub.domain.entities.button import Button
from social_hub.domain.value_objects.button_action import ButtonAction


def test_make_and_parse_callback_data():
    short_id = "abc12345"
    data = make_callback_data(short_id)
    assert data == f"sh:{short_id}"
    assert parse_callback_data(data) == short_id


def test_parse_callback_data_unrelated_returns_none():
    assert parse_callback_data("buy:123") is None
    assert parse_callback_data("") is None


def test_callback_data_within_64_bytes():
    short_id = "abcdefghijk"  # 11 chars (encode_short_id output length)
    data = make_callback_data(short_id)
    assert len(data.encode()) <= 64


def test_buttons_to_outgoing_url_button():
    btn = Button(
        id=uuid.uuid4(),
        post_id=uuid.uuid4(),
        action_type=ButtonAction.URL,
        label="Visit",
        payload={"url": "https://example.com"},
        short_id="abc12345",
    )
    rows = buttons_to_outgoing([btn])
    assert len(rows) == 1
    assert rows[0][0].url == "https://example.com"
    assert rows[0][0].callback_data is None


def test_buttons_to_outgoing_callback_button():
    btn = Button(
        id=uuid.uuid4(),
        post_id=uuid.uuid4(),
        action_type=ButtonAction.BUY,
        label="خرید",
        payload={"product_id": 1},
        short_id="xyz99999",
    )
    rows = buttons_to_outgoing([btn])
    assert rows[0][0].callback_data == "sh:xyz99999"
    assert rows[0][0].url is None


def test_buttons_to_outgoing_groups_into_rows():
    buttons = [
        Button(
            id=uuid.uuid4(),
            post_id=uuid.uuid4(),
            action_type=ButtonAction.BUY,
            label=f"Button {i}",
            payload={},
            sort_order=i,
            short_id=f"short{i:05d}",
        )
        for i in range(5)
    ]
    rows = buttons_to_outgoing(buttons, max_per_row=2)
    assert len(rows) == 3  # 2+2+1
    assert len(rows[0]) == 2
    assert len(rows[2]) == 1
