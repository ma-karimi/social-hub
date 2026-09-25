from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.social_capabilities import SocialCapabilities

SOCIAL_CAPABILITIES: dict[PlatformType, SocialCapabilities] = {
    PlatformType.TELEGRAM: SocialCapabilities(
        connect_credentials=True,
        can_publish=True,
        can_edit=True,
        can_delete=True,
        supports_buttons=True,
        supports_callback=True,
        supports_media_album=True,
        max_buttons_per_row=8,
        max_callback_data_bytes=64,
    ),
    PlatformType.BALE: SocialCapabilities(
        connect_credentials=True,
        can_publish=True,
        can_edit=True,
        can_delete=True,
        supports_buttons=True,
        supports_callback=True,
        supports_media_album=False,
        max_buttons_per_row=8,
        max_callback_data_bytes=64,
    ),
    PlatformType.EITAA: SocialCapabilities(
        connect_credentials=True,
        can_publish=True,
        can_edit=False,
        can_delete=False,
        supports_buttons=False,
        supports_callback=False,
        supports_media_album=False,
    ),
    PlatformType.INSTAGRAM: SocialCapabilities(
        connect_oauth=True,
        can_publish=True,
        can_edit=False,
        can_delete=True,
        can_schedule=True,
        supports_media_album=True,
        supports_inbox=True,
        supports_analytics=True,
        supports_automations=True,
        supports_publishing_quota=True,
    ),
}
