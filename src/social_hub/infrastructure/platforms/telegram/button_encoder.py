"""Encode Button domain entities into Telegram InlineKeyboard structures."""
from social_hub.domain.entities.button import Button
from social_hub.infrastructure.platforms.dto.outgoing_button import OutgoingButton

CALLBACK_PREFIX = "sh:"


def make_callback_data(short_id: str) -> str:
    """Build the Telegram callback_data string from a button short ID."""
    return f"{CALLBACK_PREFIX}{short_id}"


def parse_callback_data(data: str) -> str | None:
    """Extract button short_id from callback_data. Returns None if not ours."""
    if data.startswith(CALLBACK_PREFIX):
        return data[len(CALLBACK_PREFIX):]
    return None


def build_inline_keyboard(button_rows: list[list[OutgoingButton]]) -> dict:
    """Convert OutgoingButton rows into the Telegram InlineKeyboardMarkup dict."""
    keyboard = []
    for row in button_rows:
        tg_row = []
        for btn in row:
            tg_btn: dict = {"text": btn.label}
            if btn.url:
                tg_btn["url"] = btn.url
            elif btn.callback_data:
                tg_btn["callback_data"] = btn.callback_data
            tg_row.append(tg_btn)
        keyboard.append(tg_row)
    return {"inline_keyboard": keyboard}


def buttons_to_outgoing(buttons: list[Button], max_per_row: int = 2) -> list[list[OutgoingButton]]:
    """Convert domain Button entities to OutgoingButton rows for the driver."""
    outgoing: list[OutgoingButton] = []
    for btn in sorted(buttons, key=lambda b: b.sort_order):
        if btn.action_type == "url" and btn.payload.get("url"):
            ob = OutgoingButton(label=btn.label, url=btn.payload["url"])
        elif btn.short_id:
            ob = OutgoingButton(
                label=btn.label,
                callback_data=make_callback_data(btn.short_id),
            )
        else:
            continue
        outgoing.append(ob)

    rows: list[list[OutgoingButton]] = []
    for i in range(0, len(outgoing), max_per_row):
        rows.append(outgoing[i : i + max_per_row])
    return rows
