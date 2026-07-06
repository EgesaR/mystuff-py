"""Custom application exception definitions."""


class AuthenticationError(Exception):
    """Raised when authentication fails due to invalid credentials."""


class UserAlreadyExistsError(Exception):
    """Raised when attempting to register an account that already exists."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class PermissionDeniedError(Exception):
    """Raised when a user lacks permission to access a resource."""
