from dataclasses import dataclass


@dataclass(frozen=True)
class MediaRef:
    url: str
    mime_type: str = "image/jpeg"
    sort_order: int = 0
