"""Document ingestion pipeline orchestrating validation, extraction, chunking, and indexing."""

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from askbase.ai.base import EmbeddingProvider
from askbase.ai.providers import get_embedding_provider
from askbase.core.logging import get_logger
from askbase.core.settings import get_settings
from askbase.ingestion.chunker import chunk_text
from askbase.ingestion.extractor import extract_content
from askbase.ingestion.validator import ValidatedFile
from askbase.models.chunk import DocumentChunk
from askbase.models.document import DocumentVersion
from askbase.repositories.chunk import ChunkRepository
from askbase.repositories.document import DocumentRepository

logger = get_logger(__name__)


class IngestionPipeline:
    """Orchestrates end-to-end document version processing."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.chunk_repo = ChunkRepository(session)
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.settings = get_settings()

    async def process_version(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        version: DocumentVersion,
        content: bytes,
        validated_file: ValidatedFile,
    ) -> DocumentVersion:
        """Run the ingestion pipeline on an uploaded binary.

        Pipeline stages:
        1. Mark version status as 'processing'
        2. Safely persist binary to workspace-isolated storage
        3. Extract text while preserving page/section provenance
        4. Persist ExtractedText record
        5. Apply overlapping chunking strategy
        6. Compute vector embeddings for all generated chunks
        7. Persist chunks linked to source version
        8. Mark version status as 'completed' (or 'failed' on error)
        """
        logger.info(
            f"Starting ingestion pipeline for doc={document_id} ver={version.version_number} "
            f"file={validated_file.original_filename} (hash={validated_file.content_hash[:8]}...)"
        )

        try:
            # 1. Update status to processing
            await self.doc_repo.update_version_status(version.id, "processing")

            # 2. Store binary safely
            dest_dir = Path(self.settings.STORAGE_DIR) / str(workspace_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            storage_path = dest_dir / validated_file.safe_filename
            storage_path.write_bytes(content)
            version.storage_path = str(storage_path)

            # 3. Extract text and structural passages
            extracted = extract_content(content, validated_file.file_extension)

            # 4. Save extracted text record
            await self.doc_repo.save_extracted_text(
                version_id=version.id,
                raw_text=extracted.full_text,
                page_count=extracted.page_count,
                char_count=extracted.char_count,
            )

            # 5. Create structured chunks
            raw_chunks = chunk_text(
                passages=extracted.passages,
                chunk_size=self.settings.CHUNK_SIZE,
                chunk_overlap=self.settings.CHUNK_OVERLAP,
            )

            if raw_chunks:
                # 6. Generate embeddings
                chunk_texts = [c.text for c in raw_chunks]
                embeddings = await self.embedding_provider.embed_texts(chunk_texts)

                # 7. Construct and persist chunk entities
                db_chunks: list[DocumentChunk] = []
                for i, c in enumerate(raw_chunks):
                    chunk_entity = DocumentChunk(
                        workspace_id=workspace_id,
                        document_id=document_id,
                        version_id=version.id,
                        chunk_index=c.chunk_index,
                        text=c.text,
                        char_count=c.char_count,
                        page_number=c.page_number,
                        section_heading=c.section_heading,
                    )
                    if i < len(embeddings) and embeddings[i]:
                        chunk_entity.embedding = embeddings[i]
                    db_chunks.append(chunk_entity)

                await self.chunk_repo.save_chunks(db_chunks)

            # 8. Mark status as completed
            await self.doc_repo.update_version_status(version.id, "completed")
            logger.info(
                f"Ingestion succeeded for doc={document_id} ver={version.version_number}: "
                f"{len(raw_chunks)} chunks indexed."
            )
            return version

        except Exception as e:
            error_msg = f"Ingestion failed: {e}"
            logger.error(error_msg, exc_info=True)
            await self.doc_repo.update_version_status(version.id, "failed", error_message=str(e))
            raise
