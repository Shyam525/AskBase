"""Integration tests for grounded question answering, citations, and evidence abstention."""

import pytest


@pytest.mark.asyncio
async def test_grounded_answer_with_verifiable_citations(app_client):
    """Verify Q&A generates answers grounded strictly in retrieved passages with traceable citations."""
    reg = await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Evidence Systems",
            "email": "staff@evidence.org",
            "password": "Password123!",
        },
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload authoritative document
    policy_doc = b"""# Corporate Expense Policy
Section 1. Travel expenses must be pre-approved by the department director.
Section 2. Hotel accommodations are capped at 250 dollars per night for domestic travel.
Section 3. Expense reimbursement requests must be submitted within 30 days of travel completion.
"""
    upload_res = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files={"file": ("expense_policy.md", policy_doc, "text/markdown")},
        data={"title": "Expense Policy 2026"},
        headers=headers,
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document"]["id"]

    # Ask grounded question
    qa_res = await app_client.post(
        f"/api/workspaces/{ws_id}/ask",
        json={"question": "What is the hotel accommodation cap per night?"},
        headers=headers,
    )
    assert qa_res.status_code == 200
    data = qa_res.json()

    assert data["abstained"] is False
    assert "250 dollars" in data["answer"] or "hotel" in data["answer"].lower()
    assert len(data["citations"]) > 0

    # Trace citation provenance
    citation = data["citations"][0]
    assert citation["citation_id"] == 1
    assert citation["document_id"] == doc_id
    assert citation["document_title"] == "Expense Policy 2026"
    assert citation["version_number"] == 1
    assert "hotel" in citation["cited_text"].lower()


@pytest.mark.asyncio
async def test_abstention_when_evidence_is_insufficient(app_client):
    """Critical requirement: System must explicitly ABSTAIN when evidence is insufficient."""
    reg = await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Abstention Test",
            "email": "test@abstain.org",
            "password": "Password123!",
        },
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ingest document about cryptography
    crypto_doc = b"AskBase uses Argon2id for password hashing and HMAC-SHA256 for token signing."
    await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files={"file": ("crypto.txt", crypto_doc, "text/plain")},
        data={"title": "Cryptography Specs"},
        headers=headers,
    )

    # Ask completely unrelated question
    unrelated_q = "What is the recommended recipe for baking sourdough bread?"
    qa_res = await app_client.post(
        f"/api/workspaces/{ws_id}/ask",
        json={"question": unrelated_q},
        headers=headers,
    )
    assert qa_res.status_code == 200
    data = qa_res.json()

    # Must abstain
    assert data["abstained"] is True
    assert (
        "cannot answer" in data["answer"].lower()
        or "sufficient evidence was not found" in data["answer"].lower()
    )
    assert len(data["citations"]) == 0
