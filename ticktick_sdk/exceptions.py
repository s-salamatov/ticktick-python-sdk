"""Custom exceptions for the TickTick SDK."""


class TickTickError(Exception):
    """Base exception for all TickTick SDK errors."""


class TickTickAuthError(TickTickError):
    """Authentication failed (401)."""


class TickTickForbiddenError(TickTickError):
    """Access denied (403)."""


class TickTickNotFoundError(TickTickError):
    """Resource not found (404)."""


class TickTickRateLimitError(TickTickError):
    """Rate limited (429). Retry after the suggested delay."""

    def __init__(self, message: str = "Rate limited", retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class TickTickAPIError(TickTickError):
    """Generic API error with status code and error details."""

    def __init__(self, status_code: int, error_code: str = "", error_message: str = ""):
        self.status_code = status_code
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"HTTP {status_code}: {error_code} - {error_message}")
