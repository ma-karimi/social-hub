from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.platforms.base import PlatformDriver


class DriverRegistry:
    def __init__(self) -> None:
        self._drivers: dict[PlatformType, PlatformDriver] = {}

    def register(self, driver: PlatformDriver) -> None:
        self._drivers[driver.platform_type] = driver

    def get(self, platform_type: PlatformType) -> PlatformDriver:
        driver = self._drivers.get(platform_type)
        if driver is None:
            raise KeyError(f"No driver registered for platform '{platform_type}'")
        return driver

    def supported_platforms(self) -> list[PlatformType]:
        return list(self._drivers.keys())
