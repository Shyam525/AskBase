"""Verification of ADR 0001: Binary equality vs Document Identity and duplicate hash detection."""

import pytest


@pytest.mark.asyncio
async def test_duplicate_content_hash_exposed_without_auto_merging(app_client):
    """ADR 0001 Compliance:

    Calculate and expose exact content-hash matches, but do NOT automatically
    merge or delete documents based on hash match.
    """
    reg = await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Duplicate Policy Test",
            "email": "admin@duptest.org",
            "password": "Password123!",
        },
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    shared_content = b"Exact identical byte stream uploaded to different documents."

    # 1. Upload first document
    res1 = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files={"file": ("doc_alpha.txt", shared_content, "text/plain")},
        data={"title": "Document Alpha"},
        headers=headers,
    )
    assert res1.status_code == 200
    doc1_id = res1.json()["document"]["id"]
    ver1_id = res1.json()["version"]["id"]
    content_hash = res1.json()["version"]["content_hash"]
    # No prior duplicates
    assert len(res1.json()["matching_versions_in_workspace"]) == 0

    # 2. Upload second document with identical binary content
    res2 = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files={"file": ("doc_beta.txt", shared_content, "text/plain")},
        data={"title": "Document Beta"},
        headers=headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    doc2_id = data2["document"]["id"]

    # Verify distinct document identities are maintained (no auto-merge!)
    assert doc2_id != doc1_id

    # Verify exact content-hash match is detected and exposed in response
    matching = data2["matching_versions_in_workspace"]
    assert len(matching) == 1
    assert matching[0]["id"] == ver1_id
    assert matching[0]["content_hash"] == content_hash

    # 3. List documents to verify both records persist independently
    list_res = await app_client.get(
        f"/api/workspaces/{ws_id}/documents",
        headers=headers,
    )
    assert list_res.status_code == 200
    docs = list_res.json()
    doc_ids = [d["id"] for d in docs]
    assert doc1_id in doc_ids
    assert doc2_id in doc_ids
