"""Document and DocumentVersion domain models preserving full provenance and immutability."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from askbase.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from askbase.models.chunk import DocumentChunk
    from askbase.models.user import User
    from askbase.models.workspace import Workspace


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logical document identity within a workspace."""

    __tablename__ = "documents"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="documents", lazy="selectin"
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
        lazy="selectin",
    )

    @property
    def latest_version(self) -> "DocumentVersion | None":
        """Retrieve the latest immutable version if loaded in memory."""
        if "versions" in self.__dict__ and self.versions:
            return self.versions[-1]
        return None


class DocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable snapshot of a document upload."""

    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ingestion_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="versions", lazy="selectin"
    )
    created_by: Mapped["User"] = relationship("User", lazy="selectin")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
        lazy="selectin",
    )
    extracted_text: Mapped["ExtractedText | None"] = relationship(
        "ExtractedText",
        back_populates="version",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
        Index("idx_docver_hash_doc", "content_hash", "document_id"),
    )


class ExtractedText(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted text body for a specific immutable document version."""

    __tablename__ = "extracted_texts"

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    version: Mapped["DocumentVersion"] = relationship(
        "DocumentVersion", back_populates="extracted_text", lazy="selectin"
    )
