"""Cryptographic functions for password hashing and JWT issuance."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from askbase.core.errors import UnauthorizedError
from askbase.core.settings import get_settings

# Initialize Argon2 hasher with secure parameters
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
)


def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against stored Argon2 hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def generate_secure_token(length_bytes: int = 48) -> str:
    """Generate a high-entropy, cryptographically secure random token."""
    return secrets.token_urlsafe(length_bytes)


def create_access_token(
    user_id: UUID | str,
    email: str,
    role: str = "member",
    workspace_id: UUID | str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Sign and create an HMAC-SHA256 JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires = now + (
        expires_delta if expires_delta else timedelta(minutes=settings.JWT_EXPIRES_IN_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    if workspace_id:
        payload["tenant_id"] = str(workspace_id)

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate and decode JWT access token with strict claims verification."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise UnauthorizedError("Access token has expired.") from e
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError("Invalid access token.") from e
