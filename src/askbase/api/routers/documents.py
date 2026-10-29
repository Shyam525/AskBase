"""Document upload, version history, and provenance router."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from askbase.api.deps import (
    CurrentUser,
    DBSession,
    WorkspaceMember,
    require_role,
)
from askbase.api.schemas.document import (
    DocumentDetailResponse,
    DocumentSummary,
    DocumentUploadResponse,
    VersionSummary,
)
from askbase.services.document import DocumentService

router = APIRouter(prefix="/api/workspaces/{workspace_id}/documents", tags=["Documents"])


def _to_version_summary(v) -> VersionSummary:
    return VersionSummary(
        id=v.id,
        version_number=v.version_number,
        file_name=v.file_name,
        file_size_bytes=v.file_size_bytes,
        mime_type=v.mime_type,
        content_hash=v.content_hash,
        ingestion_status=v.ingestion_status,
        error_message=v.error_message,
        created_at=v.created_at,
    )


def _to_doc_summary(doc, latest_version=None) -> DocumentSummary:
    latest = latest_version or doc.latest_version
    return DocumentSummary(
        id=doc.id,
        workspace_id=doc.workspace_id,
        title=doc.title,
        description=doc.description,
        is_deleted=doc.is_deleted,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        latest_version=_to_version_summary(latest) if latest else None,
    )


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    workspace_id: uuid.UUID,
    _membership: WorkspaceMember,
    user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
):
    """Upload a new document (version 1) to the workspace."""
    content = await file.read()
    service = DocumentService(db)
    result = await service.upload_document(
        workspace_id=workspace_id,
        user_id=user.id,
        file_bytes=content,
        filename=file.filename or "upload",
        title=title,
        description=description,
    )

    return DocumentUploadResponse(
        document=_to_doc_summary(result.document, latest_version=result.version),
        version=_to_version_summary(result.version),
        matching_versions_in_workspace=[
            _to_version_summary(v) for v in result.matching_versions_in_workspace
        ],
    )


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    workspace_id: uuid.UUID,
    _membership: WorkspaceMember,
    db: DBSession,
):
    """List active documents in this workspace with their latest version info."""
    service = DocumentService(db)
    docs = await service.list_documents(workspace_id)
    return [_to_doc_summary(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    _membership: WorkspaceMember,
    db: DBSession,
):
    """Get full document metadata and immutable version history."""
    service = DocumentService(db)
    doc = await service.get_document(workspace_id, document_id)
    return DocumentDetailResponse(
        id=doc.id,
        workspace_id=doc.workspace_id,
        title=doc.title,
        description=doc.description,
        is_deleted=doc.is_deleted,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        versions=[_to_version_summary(v) for v in doc.versions],
    )


@router.post("/{document_id}/versions", response_model=DocumentUploadResponse)
async def upload_new_version(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    _membership: WorkspaceMember,
    user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
):
    """Upload a new immutable version without mutating historical snapshots."""
    content = await file.read()
    service = DocumentService(db)
    result = await service.upload_new_version(
        workspace_id=workspace_id,
        document_id=document_id,
        user_id=user.id,
        file_bytes=content,
        filename=file.filename or "upload",
    )

    return DocumentUploadResponse(
        document=_to_doc_summary(result.document, latest_version=result.version),
        version=_to_version_summary(result.version),
        matching_versions_in_workspace=[
            _to_version_summary(v) for v in result.matching_versions_in_workspace
        ],
    )


@router.delete(
    "/{document_id}",
    dependencies=[Depends(require_role("admin"))],
)
async def delete_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    db: DBSession,
):
    """Soft-delete a document (requires admin or owner privileges)."""
    service = DocumentService(db)
    await service.soft_delete_document(workspace_id, document_id)
    return {"message": "Document deleted successfully."}


@router.get("/{document_id}/versions/{version_id}/download")
async def download_document_version(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    _membership: WorkspaceMember,
    db: DBSession,
):
    """Download the exact binary file for an immutable document version."""
    service = DocumentService(db)
    content, filename, mime_type = await service.get_version_file_bytes(
        workspace_id=workspace_id,
        document_id=document_id,
        version_id=version_id,
    )
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
