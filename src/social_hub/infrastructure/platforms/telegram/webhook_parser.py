"""Parse raw Telegram update dicts into IncomingEvent DTOs."""
from social_hub.infrastructure.platforms.dto.incoming_event import IncomingEvent, IncomingEventType
from social_hub.infrastructure.platforms.telegram.button_encoder import parse_callback_data


def parse_update(raw: dict) -> IncomingEvent | None:
    """
    Parse a Telegram Update object.
    Returns IncomingEvent for callback_query or None for unhandled update types.
    """
    if "callback_query" in raw:
        return _parse_callback_query(raw)
    return None


def _parse_callback_query(raw: dict) -> IncomingEvent:
    cq = raw["callback_query"]
    data = cq.get("data", "")
    short_id = parse_callback_data(data)

    chat_id: str | None = None
    message_id: str | None = None
    msg = cq.get("message")
    if msg:
        chat_id = str(msg["chat"]["id"])
        message_id = str(msg["message_id"])

    return IncomingEvent(
        event_type=IncomingEventType.CALLBACK,
        user_ref=str(cq["from"]["id"]),
        raw=raw,
        button_short_id=short_id,
        reply_chat_id=chat_id,
        reply_message_id=message_id,
        callback_query_id=cq.get("id"),
    )
