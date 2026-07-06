from dataclasses import dataclass
from enum import StrEnum


class IncomingEventType(StrEnum):
    CALLBACK = "callback"
    MESSAGE = "message"
    WEBHOOK = "webhook"


@dataclass
class IncomingEvent:
    event_type: IncomingEventType
    user_ref: str
    raw: dict
    button_short_id: str | None = None
    reply_chat_id: str | None = None
    reply_message_id: str | None = None
    callback_query_id: str | None = None
