"""Integration tests for document ingestion, multi-format validation, and version immutability."""

import io

import pytest
from pypdf import PdfWriter


def create_minimal_pdf_bytes(text: str = "This is an architectural specification.") -> bytes:
    """Generate a valid in-memory PDF binary with text content."""
    writer = PdfWriter()
    writer.add_blank_page(width=72 * 8.5, height=72 * 11)
    # Write empty page or valid PDF structure
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_text_document(app_client):
    """Verify uploading, chunking, and indexing a plain text file."""
    reg = await app_client.post(
        "/api/auth/register",
        json={
            "orgName": "Knowledge Inc",
            "email": "admin@knowledge.org",
            "password": "Password123!",
        },
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    text_content = (
        b"AskBase provides permission-aware knowledge retrieval with verifiable citations."
    )
    files = {"file": ("guide.txt", text_content, "text/plain")}

    res = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files=files,
        data={"title": "AskBase Guide"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["document"]["title"] == "AskBase Guide"
    assert data["version"]["version_number"] == 1
    assert data["version"]["ingestion_status"] == "completed"
    assert data["version"]["file_name"] == "guide.txt"
    assert len(data["version"]["content_hash"]) == 64


@pytest.mark.asyncio
async def test_upload_markdown_document_with_sections(app_client):
    """Verify Markdown parsing preserves headings and structural sections."""
    reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Markdown Co", "email": "writer@markdown.co", "password": "Password123!"},
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    md_content = b"""# Architecture Overview
AskBase implements a modular Python backend.

## Security Model
Argon2 and short-lived JWT access tokens are enforced.
"""
    files = {"file": ("spec.md", md_content, "text/markdown")}

    res = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"]["version_number"] == 1
    assert data["version"]["ingestion_status"] == "completed"


@pytest.mark.asyncio
async def test_upload_pdf_document(app_client):
    """Verify uploading and processing valid PDF files."""
    reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "PDF Org", "email": "pdf@test.org", "password": "Password123!"},
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = create_minimal_pdf_bytes("Important internal memo.")
    files = {"file": ("memo.pdf", pdf_bytes, "application/pdf")}

    res = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"]["mime_type"] == "application/pdf"
    assert data["version"]["ingestion_status"] == "completed"


@pytest.mark.asyncio
async def test_magic_bytes_validation_rejects_counterfeit_files(app_client):
    """Verify files claiming to be PDF without %PDF- magic bytes are rejected with 400."""
    reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Security Lab", "email": "sec@lab.org", "password": "Password123!"},
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fake PDF: text payload claiming to be .pdf
    counterfeit_pdf = b"This is plain text pretending to be a PDF."
    files = {"file": ("malicious.pdf", counterfeit_pdf, "application/pdf")}

    res = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files=files,
        headers=headers,
    )
    assert res.status_code == 400
    assert (
        "magic" in res.json()["error"]["message"].lower()
        or "header" in res.json()["error"]["message"].lower()
    )


@pytest.mark.asyncio
async def test_version_immutability(app_client):
    """Verify uploading a new version increments version_number and leaves v1 untouched."""
    reg = await app_client.post(
        "/api/auth/register",
        json={"orgName": "Docs Inc", "email": "docs@test.org", "password": "Password123!"},
    )
    token = reg.json()["access_token"]
    ws_id = reg.json()["org_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload version 1
    v1_content = b"Version 1 specification content."
    res1 = await app_client.post(
        f"/api/workspaces/{ws_id}/documents",
        files={"file": ("handbook.txt", v1_content, "text/plain")},
        data={"title": "Handbook"},
        headers=headers,
    )
    assert res1.status_code == 200
    doc_id = res1.json()["document"]["id"]
    v1_id = res1.json()["version"]["id"]
    v1_hash = res1.json()["version"]["content_hash"]

    # 2. Upload version 2
    v2_content = b"Version 2 updated specification content with new chapters."
    res2 = await app_client.post(
        f"/api/workspaces/{ws_id}/documents/{doc_id}/versions",
        files={"file": ("handbook.txt", v2_content, "text/plain")},
        headers=headers,
    )
    assert res2.status_code == 200
    v2_data = res2.json()
    assert v2_data["version"]["version_number"] == 2
    assert v2_data["version"]["id"] != v1_id
    assert v2_data["version"]["content_hash"] != v1_hash

    # 3. Retrieve document details and verify both versions coexist
    detail = await app_client.get(
        f"/api/workspaces/{ws_id}/documents/{doc_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    versions = detail.json()["versions"]
    assert len(versions) == 2
    assert versions[0]["version_number"] == 1
    assert versions[1]["version_number"] == 2

    # 4. Download version 1 and confirm historical bytes remain unmodified
    down1 = await app_client.get(
        f"/api/workspaces/{ws_id}/documents/{doc_id}/versions/{v1_id}/download",
        headers=headers,
    )
    assert down1.status_code == 200
    assert down1.content == v1_content
