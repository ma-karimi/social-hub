from social_hub.domain.error_codes import ErrorCode


class SocialHubError(Exception):
    """Base exception for all domain errors."""

    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str = "", *, error_code: ErrorCode | None = None):
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class TenantNotFoundError(SocialHubError):
    error_code = ErrorCode.NOT_FOUND


class ConnectionNotFoundError(SocialHubError):
    error_code = ErrorCode.ACCOUNT_NOT_FOUND


class AccountNotFoundError(SocialHubError):
    error_code = ErrorCode.ACCOUNT_NOT_FOUND


class PostNotFoundError(SocialHubError):
    error_code = ErrorCode.POST_NOT_FOUND


class PublicationNotFoundError(SocialHubError):
    error_code = ErrorCode.NOT_FOUND


class DuplicatePostError(SocialHubError):
    """Raised when a post with the same external_ref already exists for this tenant."""

    error_code = ErrorCode.CONFLICT


class CapabilityNotSupportedError(SocialHubError):
    """Platform does not support the requested operation."""

    error_code = ErrorCode.CAPABILITY_NOT_SUPPORTED

    def __init__(self, platform: str, capability: str):
        super().__init__(f"Platform '{platform}' does not support '{capability}'")
        self.platform = platform
        self.capability = capability


class InvalidCredentialsError(SocialHubError):
    error_code = ErrorCode.INVALID_CREDENTIALS


class InvalidApiKeyError(SocialHubError):
    error_code = ErrorCode.UNAUTHORIZED


class FeatureRequiresFacebookLoginError(SocialHubError):
    error_code = ErrorCode.FEATURE_REQUIRES_FACEBOOK_LOGIN

    def __init__(self, feature: str):
        super().__init__(f"Feature '{feature}' requires a Facebook Login connection")
        self.feature = feature


class FeatureDisabledForTenantError(SocialHubError):
    error_code = ErrorCode.FEATURE_DISABLED_FOR_TENANT

    def __init__(self, feature: str):
        super().__init__(f"Feature '{feature}' is disabled for this tenant")
        self.feature = feature


class InvalidConnectTokenError(SocialHubError):
    error_code = ErrorCode.INVALID_CONNECT_TOKEN


class ConnectTokenExpiredError(SocialHubError):
    error_code = ErrorCode.CONNECT_TOKEN_EXPIRED


class UpstreamError(SocialHubError):
    error_code = ErrorCode.UPSTREAM_ERROR

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class PlatformNotSupportedError(SocialHubError):
    error_code = ErrorCode.PLATFORM_NOT_SUPPORTED
