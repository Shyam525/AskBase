"""Document and version management service."""

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from askbase.core.errors import NotFoundError
from askbase.core.settings import get_settings
from askbase.ingestion.pipeline import IngestionPipeline
from askbase.ingestion.validator import validate_file_upload
from askbase.models.document import Document, DocumentVersion
from askbase.repositories.document import DocumentRepository


@dataclass(frozen=True)
class DocumentUploadResult:
    """Result of document or version upload with duplicate hash exposure."""

    document: Document
    version: DocumentVersion
    matching_versions_in_workspace: list[DocumentVersion]


class DocumentService:
    """Coordinates document lifecycles, version immutability, and duplicate detection."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.pipeline = IngestionPipeline(session)
        self.settings = get_settings()

    async def upload_document(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        title: str | None = None,
        description: str | None = None,
    ) -> DocumentUploadResult:
        """Upload a new document with an initial immutable version (v1).

        Identifies identical content hashes without automatically merging or deleting.
        """
        validated = validate_file_upload(
            content=file_bytes,
            filename=filename,
            max_size_bytes=self.settings.MAX_UPLOAD_SIZE_BYTES,
        )

        doc_title = title.strip() if title and title.strip() else validated.original_filename

        # Detect matching content hashes in workspace (ADR 0001)
        matching_versions = await self.doc_repo.find_matching_versions_in_workspace(
            workspace_id=workspace_id,
            content_hash=validated.content_hash,
        )

        # 1. Create logical document
        document = await self.doc_repo.create_document(
            workspace_id=workspace_id,
            title=doc_title,
            description=description,
        )

        # 2. Create version 1
        version = await self.doc_repo.create_version(
            document_id=document.id,
            version_number=1,
            file_name=validated.original_filename,
            file_size_bytes=validated.file_size_bytes,
            mime_type=validated.mime_type,
            content_hash=validated.content_hash,
            storage_path="",  # Populated during ingestion
            created_by_user_id=user_id,
        )

        # 3. Execute ingestion pipeline (extract, chunk, index)
        await self.pipeline.process_version(
            workspace_id=workspace_id,
            document_id=document.id,
            version=version,
            content=file_bytes,
            validated_file=validated,
        )

        return DocumentUploadResult(
            document=document,
            version=version,
            matching_versions_in_workspace=matching_versions,
        )

    async def upload_new_version(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
    ) -> DocumentUploadResult:
        """Append a new immutable version to an existing document without altering historical snapshots."""
        document = await self.doc_repo.get_document_by_id(workspace_id, document_id)
        if not document:
            raise NotFoundError("Document not found.")

        validated = validate_file_upload(
            content=file_bytes,
            filename=filename,
            max_size_bytes=self.settings.MAX_UPLOAD_SIZE_BYTES,
        )

        # Detect duplicate content hashes across workspace
        matching_versions = await self.doc_repo.find_matching_versions_in_workspace(
            workspace_id=workspace_id,
            content_hash=validated.content_hash,
        )

        next_version_num = await self.doc_repo.get_next_version_number(document_id)

        version = await self.doc_repo.create_version(
            document_id=document.id,
            version_number=next_version_num,
            file_name=validated.original_filename,
            file_size_bytes=validated.file_size_bytes,
            mime_type=validated.mime_type,
            content_hash=validated.content_hash,
            storage_path="",
            created_by_user_id=user_id,
        )

        await self.pipeline.process_version(
            workspace_id=workspace_id,
            document_id=document.id,
            version=version,
            content=file_bytes,
            validated_file=validated,
        )

        return DocumentUploadResult(
            document=document,
            version=version,
            matching_versions_in_workspace=matching_versions,
        )

    async def list_documents(self, workspace_id: uuid.UUID) -> list[Document]:
        """List active documents in workspace."""
        return await self.doc_repo.list_documents(workspace_id)

    async def get_document(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document:
        """Fetch document details including full version history."""
        doc = await self.doc_repo.get_document_by_id(workspace_id, document_id)
        if not doc:
            raise NotFoundError("Document not found.")
        return doc

    async def soft_delete_document(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> bool:
        """Soft-delete document while preserving immutable version history and citations."""
        deleted = await self.doc_repo.soft_delete_document(workspace_id, document_id)
        if not deleted:
            raise NotFoundError("Document not found.")
        return True

    async def get_version_file_bytes(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        """Read and return stored binary bytes, filename, and MIME type."""
        doc = await self.get_document(workspace_id, document_id)
        version = next((v for v in doc.versions if v.id == version_id), None)
        if not version or not version.storage_path:
            raise NotFoundError("Document version not found.")

        path = Path(version.storage_path)
        if not path.is_file():
            raise NotFoundError("Underlying binary file not found on storage disk.")

        return path.read_bytes(), version.file_name, version.mime_type
