"""Integration tests for user authentication and session management."""

import pytest


@pytest.mark.asyncio
async def test_register_flow(app_client):
    """Verify user registration creates user and workspace, issuing tokens."""
    res = await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Acme Global",
            "email": "founder@acme.org",
            "password": "Password123!",
            "name": "Acme Founder",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["email"] == "founder@acme.org"
    assert data["role"] == "owner"
    assert data["org_id"] is not None


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(app_client):
    """Verify duplicate registration fails with 409 RESOURCE_CONFLICT."""
    payload = {
        "orgName": "First Org",
        "email": "duplicate@test.com",
        "password": "Password123!",
    }
    res1 = await app_client.post("/api/auth/register", json=payload)
    assert res1.status_code == 200

    # Attempt registration with identical email (different case)
    payload["email"] = "DUPLICATE@test.com"
    res2 = await app_client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "RESOURCE_CONFLICT"


@pytest.mark.asyncio
async def test_login_success_and_failure(app_client):
    """Verify login validation with correct and incorrect credentials."""
    await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Beta Corp",
            "email": "user@beta.corp",
            "password": "CorrectPassword123!",
        },
    )

    # 1. Invalid password
    bad_login = await app_client.post(
        "/api/auth/login",
        json={
            "email": "user@beta.corp",
            "password": "WrongPassword!",
        },
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Correct password
    good_login = await app_client.post(
        "/api/auth/login",
        json={
            "email": "user@beta.corp",
            "password": "CorrectPassword123!",
        },
    )
    assert good_login.status_code == 200
    assert "access_token" in good_login.json()


@pytest.mark.asyncio
async def test_get_current_user_me(app_client):
    """Verify GET /api/auth/me returns authenticated profile."""
    reg = await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Gamma Inc",
            "email": "engineer@gamma.inc",
            "password": "Password123!",
            "name": "Senior Staff",
        },
    )
    token = reg.json()["access_token"]

    # 1. Missing Authorization header
    unauth = await app_client.get("/api/auth/me")
    assert unauth.status_code == 401

    # 2. Valid Authorization header
    res = await app_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "engineer@gamma.inc"
    assert data["name"] == "Senior Staff"
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["name"] == "Gamma Inc"


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_logout(app_client):
    """Verify refresh token rotation and revocation upon logout."""
    reg = await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Delta Labs",
            "email": "delta@labs.io",
            "password": "Password123!",
        },
    )
    initial_refresh = reg.json()["refresh_token"]

    # 1. Rotate refresh token
    ref_res = await app_client.post(
        "/api/auth/refresh",
        json={"refreshToken": initial_refresh},
    )
    assert ref_res.status_code == 200
    new_refresh = ref_res.json()["refresh_token"]
    assert new_refresh != initial_refresh

    # 2. Old refresh token must be rejected (single-use rotation)
    stale_res = await app_client.post(
        "/api/auth/refresh",
        json={"refreshToken": initial_refresh},
    )
    assert stale_res.status_code == 401

    # 3. Logout revokes active refresh token
    logout_res = await app_client.post(
        "/api/auth/logout",
        json={"refreshToken": new_refresh},
    )
    assert logout_res.status_code == 200

    # 4. Using revoked token after logout fails
    post_logout_res = await app_client.post(
        "/api/auth/refresh",
        json={"refreshToken": new_refresh},
    )
    assert post_logout_res.status_code == 401
