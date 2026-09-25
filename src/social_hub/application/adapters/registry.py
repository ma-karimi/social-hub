from social_hub.application.adapters.base import PlatformAdapter
from social_hub.domain.exceptions import PlatformNotSupportedError
from social_hub.domain.value_objects.platform_type import PlatformType


class PlatformAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[PlatformType, PlatformAdapter] = {}

    def register(self, adapter: PlatformAdapter) -> None:
        self._adapters[adapter.platform] = adapter

    def get(self, platform: PlatformType) -> PlatformAdapter:
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise PlatformNotSupportedError(f"Platform '{platform}' is not supported")
        return adapter

    def supported_platforms(self) -> list[PlatformType]:
        return list(self._adapters.keys())

    def has(self, platform: PlatformType) -> bool:
        return platform in self._adapters
