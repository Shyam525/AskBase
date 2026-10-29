"""Integration tests for workspace isolation, tenant boundaries, and role hierarchy."""

import pytest


@pytest.mark.asyncio
async def test_workspace_creation_and_listing(app_client):
    """Verify user can create and list multiple workspaces."""
    reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Workspace 1", "email": "w1@test.com", "password": "Password123!"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create additional workspace
    create_res = await app_client.post(
        "/api/workspaces",
        json={"name": "Workspace 2", "slug": "workspace-2"},
        headers=headers,
    )
    assert create_res.status_code == 200
    w2 = create_res.json()
    assert w2["name"] == "Workspace 2"

    # List workspaces
    list_res = await app_client.get("/api/workspaces", headers=headers)
    assert list_res.status_code == 200
    workspaces = list_res.json()
    assert len(workspaces) == 2


@pytest.mark.asyncio
async def test_cross_workspace_isolation_fails_closed(app_client):
    """Strict tenant isolation: A registered user must NOT access another tenant's workspace."""
    # Register Tenant A
    reg_a = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Tenant A", "email": "admin@tenant-a.com", "password": "Password123!"},
    )
    token_a = reg_a.json()["access_token"]
    org_a_id = reg_a.json()["org_id"]

    # Register Tenant B
    reg_b = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Tenant B", "email": "admin@tenant-b.com", "password": "Password123!"},
    )
    token_b = reg_b.json()["access_token"]

    # Tenant B tries to access Tenant A's workspace details
    tampered_access = await app_client.get(
        f"/api/workspaces/{org_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert tampered_access.status_code == 403
    assert tampered_access.json()["error"]["code"] == "FORBIDDEN"

    # Tenant B tries to list Tenant A's members
    tampered_members = await app_client.get(
        f"/api/workspaces/{org_a_id}/members",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert tampered_members.status_code == 403
    assert tampered_members.json()["error"]["code"] == "FORBIDDEN"

    # Tenant A accesses Tenant A's workspace successfully
    valid_access = await app_client.get(
        f"/api/workspaces/{org_a_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert valid_access.status_code == 200


@pytest.mark.asyncio
async def test_membership_roles_and_privileges(app_client):
    """Verify role authorization hierarchy (owner > admin > member)."""
    # 1. Register Owner
    owner_reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Security Co", "email": "owner@security.co", "password": "Password123!"},
    )
    owner_token = owner_reg.json()["access_token"]
    ws_id = owner_reg.json()["org_id"]

    # 2. Register regular user
    user_reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Other Org", "email": "worker@security.co", "password": "Password123!"},
    )
    worker_token = user_reg.json()["access_token"]
    worker_id = user_reg.json()["user_id"]

    # 3. Owner adds worker as 'member'
    add_res = await app_client.post(
        f"/api/workspaces/{ws_id}/members",
        json={"email": "worker@security.co", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert add_res.status_code == 200
    assert add_res.json()["role"] == "member"

    # 4. Worker (role=member) attempts to invite someone else (requires admin/owner)
    unauthorized_invite = await app_client.post(
        f"/api/workspaces/{ws_id}/members",
        json={"email": "worker@security.co", "role": "member"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert unauthorized_invite.status_code == 403
    assert "privileges" in unauthorized_invite.json()["error"]["message"].lower()

    # 5. Owner removes member
    del_res = await app_client.delete(
        f"/api/workspaces/{ws_id}/members/{worker_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert del_res.status_code == 200
