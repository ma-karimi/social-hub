from dataclasses import dataclass


@dataclass
class OutgoingButton:
    label: str
    callback_data: str | None = None
    url: str | None = None
