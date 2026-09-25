from social_hub.api.i18n.messages import resolve_locale, translate
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import SocialHubError


def error_body(
    error_code: ErrorCode | str,
    *,
    locale: str = "en",
    message: str | None = None,
) -> dict:
    code = ErrorCode(error_code) if not isinstance(error_code, ErrorCode) else error_code
    return {
        "error_code": code.value,
        "message": message or translate(code, locale),
    }


def status_for_code(code: ErrorCode) -> int:
    mapping = {
        ErrorCode.UNAUTHORIZED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.ACCOUNT_NOT_FOUND: 404,
        ErrorCode.POST_NOT_FOUND: 404,
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.FEATURE_REQUIRES_FACEBOOK_LOGIN: 400,
        ErrorCode.FEATURE_DISABLED_FOR_TENANT: 400,
        ErrorCode.INVALID_CONNECT_TOKEN: 400,
        ErrorCode.CONNECT_TOKEN_EXPIRED: 400,
        ErrorCode.MISSING_MEDIA: 400,
        ErrorCode.UNSUPPORTED_OPERATION: 400,
        ErrorCode.PLATFORM_NOT_SUPPORTED: 400,
        ErrorCode.CAPABILITY_NOT_SUPPORTED: 400,
        ErrorCode.INVALID_CREDENTIALS: 400,
        ErrorCode.CONFLICT: 409,
        ErrorCode.DUPLICATE_CONTENT: 409,
        ErrorCode.RATE_LIMITED: 429,
        ErrorCode.QUOTA_EXCEEDED: 429,
        ErrorCode.PARTIAL_FAILURE: 207,
        ErrorCode.MEDIA_FETCH_FAILED: 502,
        ErrorCode.UPSTREAM_ERROR: 502,
        ErrorCode.INTERNAL_ERROR: 500,
    }
    return mapping.get(code, 500)


def error_from_exception(exc: Exception, *, locale: str = "en") -> tuple[int, dict]:
    if isinstance(exc, SocialHubError):
        status = status_for_code(exc.error_code)
        body = error_body(exc.error_code, locale=locale)
        return status, body
    return 500, error_body(ErrorCode.INTERNAL_ERROR, locale=locale)


_status_for_code = status_for_code

__all__ = [
    "error_body",
    "error_from_exception",
    "resolve_locale",
    "translate",
    "status_for_code",
]
