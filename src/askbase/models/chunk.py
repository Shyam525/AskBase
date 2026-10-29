"""Searchable chunk persistence model."""

import json
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from askbase.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from askbase.models.document import Document, DocumentVersion
    from askbase.models.workspace import Workspace


class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Searchable passage derived from an immutable document version."""

    __tablename__ = "document_chunks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Serialized vector embedding
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    version: Mapped["DocumentVersion"] = relationship(
        "DocumentVersion", back_populates="chunks", lazy="selectin"
    )
    document: Mapped["Document"] = relationship("Document", lazy="selectin")
    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="selectin")

    @property
    def embedding(self) -> list[float] | None:
        """Parse embedding JSON array into floats."""
        if not self.embedding_json:
            return None
        try:
            val = json.loads(self.embedding_json)
            return [float(x) for x in val] if isinstance(val, list) else None
        except Exception:
            return None

    @embedding.setter
    def embedding(self, values: list[float] | None) -> None:
        """Serialize float array to JSON."""
        if values is None:
            self.embedding_json = None
        else:
            self.embedding_json = json.dumps(values)

    __table_args__ = (
        Index("idx_chunks_ws_doc_ver", "workspace_id", "document_id", "version_id"),
        Index("idx_chunks_version_idx", "version_id", "chunk_index"),
    )
