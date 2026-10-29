"""Unit tests for configuration validation and fail-closed security rules."""

import pytest
from pydantic import ValidationError

from askbase.core.settings import DEVELOPMENT_JWT_SECRET, Settings, reset_settings


def test_valid_default_settings():
    """Verify default development configuration loads properly."""
    reset_settings()
    settings = Settings(
        NODE_ENV="development",
        PORT=5000,
        DATABASE_URL="postgresql://postgres:secret@localhost:5432/askbase_dev",
    )
    assert settings.ENVIRONMENT == "development"
    assert settings.PORT == 5000
    assert (
        settings.DATABASE_URL == "postgresql+asyncpg://postgres:secret@localhost:5432/askbase_dev"
    )
    assert settings.JWT_SECRET == DEVELOPMENT_JWT_SECRET
    assert settings.JWT_ISSUER == "askbase-api"


def test_uses_fallback_jwt_secret_in_development_and_test():
    """Verify non-production environments supply fallback secret when omitted."""
    dev_settings = Settings(NODE_ENV="development", JWT_SECRET="")
    test_settings = Settings(NODE_ENV="test", JWT_SECRET="")

    assert dev_settings.JWT_SECRET == DEVELOPMENT_JWT_SECRET
    assert test_settings.JWT_SECRET == DEVELOPMENT_JWT_SECRET
    assert len(dev_settings.JWT_SECRET) >= 32


def test_rejects_invalid_port_numbers():
    """Verify out-of-range port numbers raise ValidationError."""
    with pytest.raises(ValidationError):
        Settings(PORT=70000)

    with pytest.raises(ValidationError):
        Settings(PORT=-1)


def test_enforces_production_jwt_secret_strictness():
    """Production mode must fail closed if JWT_SECRET is missing, short, or placeholder."""
    # 1. Missing secret in production
    with pytest.raises(ValidationError) as exc:
        Settings(NODE_ENV="production", JWT_SECRET="")
    assert "at least 32 characters in production" in str(exc.value)

    # 2. Short secret in production (< 32 chars)
    with pytest.raises(ValidationError) as exc:
        Settings(NODE_ENV="production", JWT_SECRET="too-short-secret-key")
    assert "at least 32 characters in production" in str(exc.value)

    # 3. Development placeholder secret in production
    with pytest.raises(ValidationError) as exc:
        Settings(NODE_ENV="production", JWT_SECRET=DEVELOPMENT_JWT_SECRET)
    assert "Cannot use development JWT placeholder in production" in str(exc.value)

    # 4. Valid production secret
    prod = Settings(
        NODE_ENV="production",
        JWT_SECRET="a-very-secure-production-secret-with-more-than-32-characters!",
    )
    assert prod.ENVIRONMENT == "production"
    assert prod.JWT_SECRET == "a-very-secure-production-secret-with-more-than-32-characters!"
