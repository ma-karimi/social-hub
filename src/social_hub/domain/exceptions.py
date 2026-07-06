class SocialHubError(Exception):
    """Base exception for all domain errors."""


class TenantNotFoundError(SocialHubError):
    pass


class ConnectionNotFoundError(SocialHubError):
    pass


class PostNotFoundError(SocialHubError):
    pass


class PublicationNotFoundError(SocialHubError):
    pass


class DuplicatePostError(SocialHubError):
    """Raised when a post with the same external_ref already exists for this tenant."""
    pass


class CapabilityNotSupportedError(SocialHubError):
    """Platform does not support the requested operation."""
    def __init__(self, platform: str, capability: str):
        super().__init__(f"Platform '{platform}' does not support '{capability}'")
        self.platform = platform
        self.capability = capability


class InvalidCredentialsError(SocialHubError):
    pass


class InvalidApiKeyError(SocialHubError):
    pass
