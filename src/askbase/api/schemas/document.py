"""Document and version response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VersionSummary(BaseModel):
    """Immutable version snapshot summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    file_name: str
    file_size_bytes: int
    mime_type: str
    content_hash: str
    ingestion_status: str
    error_message: str | None = None
    created_at: datetime


class DocumentSummary(BaseModel):
    """Logical document summary with latest version information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    latest_version: VersionSummary | None = None


class DocumentDetailResponse(BaseModel):
    """Document details with complete immutable version history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    versions: list[VersionSummary]


class DocumentUploadResponse(BaseModel):
    """Upload outcome exposing created entities and duplicate content-hash warnings."""

    document: DocumentSummary
    version: VersionSummary
    matching_versions_in_workspace: list[VersionSummary]
