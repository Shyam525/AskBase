"""DocumentChunk repository for storage and retrieval access."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from askbase.models.chunk import DocumentChunk
from askbase.models.document import Document, DocumentVersion


class ChunkRepository:
    """Repository managing searchable chunks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Bulk save chunk instances."""
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def get_chunks_for_version(self, version_id: uuid.UUID) -> list[DocumentChunk]:
        """Fetch all chunks belonging to a document version."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.version_id == version_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_chunks_for_workspace(
        self,
        workspace_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> list[DocumentChunk]:
        """Retrieve all active chunks for a workspace with document and version metadata."""
        stmt = (
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(DocumentChunk.workspace_id == workspace_id)
            .options(
                selectinload(DocumentChunk.document),
                selectinload(DocumentChunk.version),
            )
        )
        if not include_deleted:
            stmt = stmt.where(Document.is_deleted.is_(False))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
