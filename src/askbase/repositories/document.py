"""Document, DocumentVersion, and ExtractedText data access repository."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from askbase.models.document import Document, DocumentVersion, ExtractedText


class DocumentRepository:
    """Repository handling document hierarchy and version persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_document(
        self,
        workspace_id: uuid.UUID,
        title: str,
        description: str | None = None,
    ) -> Document:
        """Create a new logical document within a workspace."""
        doc = Document(
            workspace_id=workspace_id,
            title=title.strip(),
            description=description.strip() if description else None,
            is_deleted=False,
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_document_by_id(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Document | None:
        """Fetch logical document ensuring strict workspace boundary."""
        stmt = (
            select(Document)
            .where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
            )
            .options(
                selectinload(Document.versions).selectinload(DocumentVersion.extracted_text),
                selectinload(Document.versions).selectinload(DocumentVersion.created_by),
            )
        )
        if not include_deleted:
            stmt = stmt.where(Document.is_deleted.is_(False))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> list[Document]:
        """List all documents belonging to a workspace."""
        stmt = (
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .options(
                selectinload(Document.versions).selectinload(DocumentVersion.created_by),
            )
            .order_by(Document.updated_at.desc())
        )
        if not include_deleted:
            stmt = stmt.where(Document.is_deleted.is_(False))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete_document(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> bool:
        """Perform safe soft-deletion preserving historical records and audit provenance."""
        doc = await self.get_document_by_id(workspace_id, document_id)
        if not doc:
            return False
        doc.is_deleted = True
        await self.session.flush()
        return True

    async def get_next_version_number(self, document_id: uuid.UUID) -> int:
        """Calculate next sequential version number for a document."""
        stmt = select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(
            DocumentVersion.document_id == document_id
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        return int(max_num) + 1

    async def create_version(
        self,
        document_id: uuid.UUID,
        version_number: int,
        file_name: str,
        file_size_bytes: int,
        mime_type: str,
        content_hash: str,
        storage_path: str,
        created_by_user_id: uuid.UUID,
    ) -> DocumentVersion:
        """Create and persist an immutable document version snapshot."""
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            content_hash=content_hash,
            storage_path=storage_path,
            created_by_user_id=created_by_user_id,
            ingestion_status="pending",
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_version_by_id(self, version_id: uuid.UUID) -> DocumentVersion | None:
        """Fetch immutable version by primary key."""
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.id == version_id)
            .options(
                selectinload(DocumentVersion.document),
                selectinload(DocumentVersion.extracted_text),
                selectinload(DocumentVersion.created_by),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_matching_versions_in_workspace(
        self,
        workspace_id: uuid.UUID,
        content_hash: str,
    ) -> list[DocumentVersion]:
        """Find any document versions in this workspace with matching binary content hash.

        Implements explicit hash matching without destructive auto-merging.
        """
        stmt = (
            select(DocumentVersion)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Document.workspace_id == workspace_id,
                DocumentVersion.content_hash == content_hash,
            )
            .options(selectinload(DocumentVersion.document))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_extracted_text(
        self,
        version_id: uuid.UUID,
        raw_text: str,
        page_count: int,
        char_count: int,
    ) -> ExtractedText:
        """Persist full extracted text for a document version."""
        record = ExtractedText(
            version_id=version_id,
            raw_text=raw_text,
            page_count=page_count,
            char_count=char_count,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def update_version_status(
        self,
        version_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update ingestion status for a document version."""
        version = await self.get_version_by_id(version_id)
        if version:
            version.ingestion_status = status
            version.error_message = error_message
            await self.session.flush()
