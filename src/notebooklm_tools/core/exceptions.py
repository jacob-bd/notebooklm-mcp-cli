"""Custom exceptions for NLM CLI."""

from typing import Any


class NLMError(Exception):
    """Base exception for all NLM errors."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        self.message = message
        self.hint = hint
        super().__init__(message)

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\n\nHint: {self.hint}"
        return self.message


class AuthenticationError(NLMError):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(
        self,
        message: str = "Authentication failed",
        hint: str = "Run 'nlm login' to authenticate.",
    ) -> None:
        super().__init__(message, hint)


class NotFoundError(NLMError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        hint: str | None = None,
    ) -> None:
        message = f"{resource_type} not found: {resource_id}"
        if hint is None:
            hint = f"Run 'nlm {resource_type.lower()} list' to see available {resource_type.lower()}s."
        super().__init__(message, hint)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ValidationError(NLMError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        hint: str | None = None,
    ) -> None:
        if field:
            message = f"Invalid {field}: {message}"
        super().__init__(message, hint)
        self.field = field


class NetworkError(NLMError):
    """Raised when a network request fails."""

    def __init__(
        self,
        message: str = "Network request failed",
        hint: str = "Check your internet connection and try again.",
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, hint)
        self.status_code = status_code


class RateLimitError(NLMError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        hint: str = "Please wait a moment and try again.",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, hint)
        self.retry_after = retry_after


class ConfigError(NLMError):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        hint: str = "Check your configuration at ~/.nlm/config.toml",
    ) -> None:
        super().__init__(message, hint)


class ProfileNotFoundError(NLMError):
    """Raised when a profile is not found."""

    def __init__(self, profile_name: str) -> None:
        message = f"Profile not found: {profile_name}"
        hint = "Run 'nlm login' to create a profile, or use '--profile <name>' to specify a different profile."
        super().__init__(message, hint)
        self.profile_name = profile_name


class AccountMismatchError(NLMError):
    """Raised when trying to save credentials for a different account than what's stored."""

    def __init__(
        self,
        stored_email: str,
        new_email: str,
        profile_name: str,
    ) -> None:
        message = (
            f"Account mismatch for profile '{profile_name}': "
            f"stored account is '{stored_email}' but received credentials for '{new_email}'"
        )
        hint = "Use 'nlm login --force' to overwrite with the new account."
        super().__init__(message, hint)
        self.stored_email = stored_email
        self.new_email = new_email
        self.profile_name = profile_name


class FileUploadError(NLMError):
    """Raised when file upload fails."""

    def __init__(self, filename: str, message: str = ""):
        self.filename = filename
        super().__init__(f"Failed to upload '{filename}': {message}" if message else f"Failed to upload '{filename}'")


class FileValidationError(NLMError):
    """Raised when file validation fails before upload."""
    pass


def handle_api_error(status_code: int, response_data: dict[str, Any] | None = None) -> NLMError:
    """Convert API error response to appropriate exception."""
    if status_code == 401:
        return AuthenticationError()
    if status_code == 403:
        return AuthenticationError(
            message="Access denied",
            hint="Your session may have expired. Run 'nlm login' to re-authenticate.",
        )
    if status_code == 404:
        return NotFoundError("Resource", "unknown")
    if status_code == 429:
        return RateLimitError()
    if status_code >= 500:
        return NetworkError(
            message="NotebookLM server error",
            hint="The NotebookLM service may be temporarily unavailable. Try again later.",
            status_code=status_code,
        )
    return NetworkError(
        message=f"Request failed with status {status_code}",
        status_code=status_code,
    )
