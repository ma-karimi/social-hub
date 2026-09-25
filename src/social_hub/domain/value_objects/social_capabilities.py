from dataclasses import dataclass


@dataclass(frozen=True)
class SocialCapabilities:
    connect_oauth: bool = False
    connect_credentials: bool = False
    can_publish: bool = True
    can_edit: bool = False
    can_delete: bool = False
    can_schedule: bool = False
    supports_buttons: bool = False
    supports_callback: bool = False
    supports_media_album: bool = False
    supports_inbox: bool = False
    supports_analytics: bool = False
    supports_automations: bool = False
    supports_publishing_quota: bool = False
    max_buttons_per_row: int = 0
    max_callback_data_bytes: int = 0
