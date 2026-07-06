from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformCapabilities:
    can_publish: bool = True
    can_edit: bool = False
    can_delete: bool = False
    supports_buttons: bool = False
    supports_callback: bool = False
    supports_media_album: bool = False
    max_buttons_per_row: int = 0
    max_callback_data_bytes: int = 0
