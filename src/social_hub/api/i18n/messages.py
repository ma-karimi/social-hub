from social_hub.domain.error_codes import ErrorCode

MESSAGES_EN: dict[str, str] = {
    ErrorCode.UNAUTHORIZED: "Unauthorized",
    ErrorCode.FORBIDDEN: "Forbidden",
    ErrorCode.NOT_FOUND: "Resource not found",
    ErrorCode.VALIDATION_ERROR: "Validation error",
    ErrorCode.INTERNAL_ERROR: "Internal server error",
    ErrorCode.RATE_LIMITED: "Rate limit exceeded",
    ErrorCode.CONFLICT: "Conflict",
    ErrorCode.DUPLICATE_CONTENT: "Duplicate content detected",
    ErrorCode.ACCOUNT_NOT_FOUND: "Social account not found",
    ErrorCode.POST_NOT_FOUND: "Post not found",
    ErrorCode.PLATFORM_NOT_SUPPORTED: "Platform is not supported",
    ErrorCode.CAPABILITY_NOT_SUPPORTED: "Capability is not supported on this platform",
    ErrorCode.FEATURE_REQUIRES_FACEBOOK_LOGIN: (
        "This feature requires an account connected with Facebook Login"
    ),
    ErrorCode.FEATURE_DISABLED_FOR_TENANT: "This feature is disabled for this tenant",
    ErrorCode.INVALID_CONNECT_TOKEN: "Invalid connect token",
    ErrorCode.CONNECT_TOKEN_EXPIRED: "Connect token has expired",
    ErrorCode.UPSTREAM_ERROR: "Upstream provider error",
    ErrorCode.MEDIA_FETCH_FAILED: "Failed to fetch media",
    ErrorCode.QUOTA_EXCEEDED: "Publishing quota exceeded",
    ErrorCode.PARTIAL_FAILURE: "Post created but publishing partially failed",
    ErrorCode.INVALID_CREDENTIALS: "Invalid credentials",
    ErrorCode.MISSING_MEDIA: "Media is required",
    ErrorCode.UNSUPPORTED_OPERATION: "Operation is not supported",
}

MESSAGES_FA: dict[str, str] = {
    ErrorCode.UNAUTHORIZED: "دسترسی غیرمجاز",
    ErrorCode.FORBIDDEN: "ممنوع",
    ErrorCode.NOT_FOUND: "منبع یافت نشد",
    ErrorCode.VALIDATION_ERROR: "خطای اعتبارسنجی",
    ErrorCode.INTERNAL_ERROR: "خطای داخلی سرور",
    ErrorCode.RATE_LIMITED: "محدودیت نرخ درخواست",
    ErrorCode.CONFLICT: "تداخل",
    ErrorCode.DUPLICATE_CONTENT: "محتوای تکراری شناسایی شد",
    ErrorCode.ACCOUNT_NOT_FOUND: "اکانت اجتماعی یافت نشد",
    ErrorCode.POST_NOT_FOUND: "پست یافت نشد",
    ErrorCode.PLATFORM_NOT_SUPPORTED: "پلتفرم پشتیبانی نمی‌شود",
    ErrorCode.CAPABILITY_NOT_SUPPORTED: "این قابلیت در این پلتفرم پشتیبانی نمی‌شود",
    ErrorCode.FEATURE_REQUIRES_FACEBOOK_LOGIN: (
        "این قابلیت نیازمند اتصال با Facebook Login است"
    ),
    ErrorCode.FEATURE_DISABLED_FOR_TENANT: "این قابلیت برای این مستأجر غیرفعال است",
    ErrorCode.INVALID_CONNECT_TOKEN: "توکن اتصال نامعتبر است",
    ErrorCode.CONNECT_TOKEN_EXPIRED: "توکن اتصال منقضی شده است",
    ErrorCode.UPSTREAM_ERROR: "خطای سرویس بالادستی",
    ErrorCode.MEDIA_FETCH_FAILED: "دریافت رسانه ناموفق بود",
    ErrorCode.QUOTA_EXCEEDED: "سهمیه انتشار تکمیل شده است",
    ErrorCode.PARTIAL_FAILURE: "پست ساخته شد اما انتشار ناقص بود",
    ErrorCode.INVALID_CREDENTIALS: "اعتبارنامه نامعتبر است",
    ErrorCode.MISSING_MEDIA: "رسانه الزامی است",
    ErrorCode.UNSUPPORTED_OPERATION: "عملیات پشتیبانی نمی‌شود",
}


def resolve_locale(accept_language: str | None) -> str:
    if not accept_language:
        return "en"
    primary = accept_language.split(",")[0].strip().lower()
    if primary.startswith("fa"):
        return "fa"
    return "en"


def translate(error_code: ErrorCode | str, locale: str = "en", fallback: str | None = None) -> str:
    code = ErrorCode(error_code) if not isinstance(error_code, ErrorCode) else error_code
    table = MESSAGES_FA if locale == "fa" else MESSAGES_EN
    return table.get(code) or fallback or MESSAGES_EN.get(code, str(code))
