from social_hub.domain.exceptions import UpstreamError


class ZernioAPIError(UpstreamError):
    """Internal-only upstream HTTP error (never expose provider name publicly)."""

    def __init__(self, message: str, *, status_code: int | None = None, body: dict | None = None):
        super().__init__(message, status_code=status_code)
        self.body = body or {}
