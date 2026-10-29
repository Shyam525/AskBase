"""Integration tests for workspace-scoped search retrieval and tenant isolation."""

import pytest


@pytest.mark.asyncio
async def test_search_scoped_to_workspace(app_client):
    """Verify search returns snippets and provenance scoped to tenant workspace."""
    # 1. Register Tenant A
    reg_a = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Search Org A", "email": "a@search.org", "password": "Password123!"},
    )
    token_a = reg_a.json()["access_token"]
    ws_a_id = reg_a.json()["org_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Ingest document in Workspace A
    content_a = b"""
    Kubernetes cluster deployment guidelines.
    Pods must be configured with resource requests and limits.
    Ingress controllers manage TLS termination and routing.
    """
    await app_client.post(
        f"/api/workspaces/{ws_a_id}/documents",
        files={"file": ("k8s.txt", content_a, "text/plain")},
        data={"title": "Kubernetes Guide"},
        headers=headers_a,
    )

    # 2. Register Tenant B
    reg_b = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Search Org B", "email": "b@search.org", "password": "Password123!"},
    )
    token_b = reg_b.json()["access_token"]
    ws_b_id = reg_b.json()["org_id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Ingest document in Workspace B with distinct content
    content_b = b"""
    PostgreSQL connection pooling configuration.
    Max connections should not exceed hardware thread saturation.
    """
    await app_client.post(
        f"/api/workspaces/{ws_b_id}/documents",
        files={"file": ("postgres.txt", content_b, "text/plain")},
        data={"title": "Database Guide"},
        headers=headers_b,
    )

    # 3. Tenant A searches for 'Kubernetes'
    search_res_a = await app_client.post(
        f"/api/workspaces/{ws_a_id}/search",
        json={"query": "Kubernetes Ingress", "mode": "hybrid"},
        headers=headers_a,
    )
    assert search_res_a.status_code == 200
    data_a = search_res_a.json()
    assert data_a["total"] > 0
    hit = data_a["results"][0]
    assert hit["document_title"] == "Kubernetes Guide"
    assert "Kubernetes" in hit["snippet"]
    assert hit["version_number"] == 1
    assert hit["score"] > 0

    # 4. Tenant B searches in Workspace B for 'Kubernetes' -> must return 0 results (isolation!)
    search_res_b = await app_client.post(
        f"/api/workspaces/{ws_b_id}/search",
        json={"query": "Kubernetes", "mode": "hybrid"},
        headers=headers_b,
    )
    assert search_res_b.status_code == 200
    assert search_res_b.json()["total"] == 0

    # 5. Tenant B attempts unauthorized search in Tenant A's workspace -> 403 Forbidden!
    unauthorized_search = await app_client.post(
        f"/api/workspaces/{ws_a_id}/search",
        json={"query": "Kubernetes", "mode": "hybrid"},
        headers=headers_b,
    )
    assert unauthorized_search.status_code == 403


@pytest.mark.asyncio
async def test_search_modes(app_client):
    """Verify lexical, semantic, and hybrid search endpoints function."""
    reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Modes Org", "email": "modes@test.org", "password": "Password123!"},
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files={
            "file": ("notes.txt", b"Microservices architecture resilience patterns.", "text/plain")
        },
        data={"title": "Patterns"},
        headers=headers,
    )

    for mode in ["lexical", "semantic", "hybrid"]:
        res = await app_client.get(
            f"/api/workspaces/{ws_id}/search?q=Microservices&mode={mode}",
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["mode"] == mode
