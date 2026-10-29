"""Structured logging configuration with request correlation and secret sanitization."""

import contextvars
import logging
import sys
from typing import Any

# Context variable for request correlation ID
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "jwt_secret",
    "secret",
    "authorization",
    "api_key",
}


class CorrelationFilter(logging.Filter):
    """Injects request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


def sanitize_sensitive_data(data: Any) -> Any:
    """Recursively scrub sensitive keys from dictionaries or structures before logging."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    if isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]
    return data


def setup_logging(log_level: str = "info") -> None:
    """Configure application-wide structured logger."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] [req_id=%(request_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers if reconfigured
    root_logger.handlers = [handler]

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retrieve named logger with correlation filter applied."""
    logger = logging.getLogger(name)
    return logger
