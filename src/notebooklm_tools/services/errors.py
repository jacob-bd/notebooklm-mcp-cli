"""Service layer errors and exceptions."""

class ServiceError(Exception):
    """Base class for all service layer errors."""
    def __init__(self, message: str, user_message: str = None, debug_code: str = None):
        super().__init__(message)
        self.user_message = user_message or message
        self.debug_code = debug_code

class ValidationError(ServiceError):
    """Raised when input parameters are invalid."""
    pass

class NotFoundError(ServiceError):
    """Raised when a resource (notebook, source, etc.) is not found."""
    pass

class CreationError(ServiceError):
    """Raised when a creation operation fails (e.g. fail-fast check)."""
    pass

class ExportError(ServiceError):
    """Raised when an export operation fails."""
    pass
