from social_hub.application.services.capability_resolver import CapabilityResolver
from social_hub.domain.value_objects.platform_type import PlatformType


def test_telegram_capabilities():
    resolver = CapabilityResolver()
    caps = resolver.resolve(PlatformType.TELEGRAM)
    assert caps.can_publish is True
    assert caps.can_edit is True
    assert caps.can_delete is True
    assert caps.supports_buttons is True
    assert caps.supports_callback is True
    assert caps.max_callback_data_bytes == 64


def test_instagram_has_no_edit():
    resolver = CapabilityResolver()
    caps = resolver.resolve(PlatformType.INSTAGRAM)
    assert caps.can_publish is True
    assert caps.can_edit is False
    assert caps.supports_buttons is False


def test_eitaa_publish_only():
    resolver = CapabilityResolver()
    caps = resolver.resolve(PlatformType.EITAA)
    assert caps.can_publish is True
    assert caps.can_edit is False
    assert caps.can_delete is False
    assert caps.supports_buttons is False
    assert caps.supports_callback is False
    assert caps.supports_media_album is False


def test_unknown_platform_returns_defaults():
    resolver = CapabilityResolver()
    from social_hub.domain.value_objects.capabilities import PlatformCapabilities
    caps = resolver.resolve("nonexistent")  # type: ignore
    assert isinstance(caps, PlatformCapabilities)
    assert caps.can_publish is True
