"""Unit tests for Argon2 password hashing and JWT issuance/validation."""

import uuid
from datetime import timedelta

import pytest

from askbase.core.errors import UnauthorizedError
from askbase.core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,
    verify_password,
)


def test_argon2_password_hashing():
    """Verify Argon2 hashes password securely and verifies matches."""
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)

    assert hashed is not None
    assert hashed != plain
    assert hashed.startswith("$argon2")

    # Correct password verifies
    assert verify_password(plain, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_issuance_and_decoding():
    """Verify access token creation and decoding of claims."""
    user_id = uuid.uuid4()
    email = "engineer@askbase.org"
    ws_id = uuid.uuid4()

    token = create_access_token(
        user_id=user_id,
        email=email,
        role="admin",
        workspace_id=ws_id,
    )
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["role"] == "admin"
    assert payload["tenant_id"] == str(ws_id)
    assert payload["iss"] == "askbase-api"
    assert payload["aud"] == "askbase-clients"


def test_jwt_tampering_rejected():
    """Verify forged or altered tokens are rejected."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, email="alice@test.com")

    # Tamper with signature
    tampered = token[:-5] + "abcde"
    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(tampered)
    assert "Invalid access token" in str(exc.value)


def test_jwt_expiration_rejected():
    """Verify expired tokens are rejected."""
    user_id = uuid.uuid4()
    expired_token = create_access_token(
        user_id=user_id,
        email="bob@test.com",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )

    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(expired_token)
    assert "Access token has expired" in str(exc.value)


def test_secure_token_generation():
    """Verify entropy and format of random tokens."""
    token1 = generate_secure_token(48)
    token2 = generate_secure_token(48)

    assert len(token1) >= 48
    assert token1 != token2
