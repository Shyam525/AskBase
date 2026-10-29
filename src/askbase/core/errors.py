"""Application operational error hierarchy."""

from typing import Any


class AppError(Exception):
    """Base operational application error.

    Represents anticipated, safe error modes that can be formatted
    and returned directly to clients without leaking sensitive stack traces.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        status_code: int = 500,
        code: str = "INTERNAL_SERVER_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        """Format error payload adhering to AskBase API contract."""
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details is not None:
            payload["details"] = self.details
        return {"error": payload}


class ValidationError(AppError):
    """Raised when request payload or parameters fail schema validation."""

    def __init__(
        self,
        message: str = "Request validation failed.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            code="VALIDATION_ERROR",
            details=details,
        )


class BadRequestError(AppError):
    """Raised when client inputs or state transitions are invalid."""

    def __init__(
        self,
        message: str = "Bad request.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            code="BAD_REQUEST",
            details=details,
        )


class UnauthorizedError(AppError):
    """Raised when authentication credentials are required or invalid."""

    def __init__(
        self,
        message: str = "Authentication required.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            code="UNAUTHORIZED",
            details=details,
        )


class ForbiddenError(AppError):
    """Raised when the authenticated user lacks permissions for an operation."""

    def __init__(
        self,
        message: str = "Access denied.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=403,
            code="FORBIDDEN",
            details=details,
        )


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "Requested resource not found.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            code="NOT_FOUND",
            details=details,
        )


class ConflictError(AppError):
    """Raised when a unique constraint or resource state conflicts."""

    def __init__(
        self,
        message: str = "Resource conflict.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=409,
            code="RESOURCE_CONFLICT",
            details=details,
        )


class ServiceUnavailableError(AppError):
    """Raised when an external dependency or database is unreachable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            details=details,
        )


class InsufficientEvidenceError(AppError):
    """Raised when an answer cannot be grounded in retrievable evidence."""

    def __init__(
        self,
        message: str = "Insufficient evidence to generate an answer.",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=200,
            code="INSUFFICIENT_EVIDENCE",
            details=details,
        )
