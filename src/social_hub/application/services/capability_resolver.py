from social_hub.domain.value_objects.capabilities import PlatformCapabilities
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.capabilities import PLATFORM_CAPABILITIES


class CapabilityResolver:
    def resolve(self, platform_type: PlatformType) -> PlatformCapabilities:
        return PLATFORM_CAPABILITIES.get(platform_type, PlatformCapabilities())
