"""Workspace and WorkspaceMembership domain models."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from askbase.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from askbase.models.document import Document
    from askbase.models.user import User


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Workspace boundary representing an organization or tenant."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)

    # Relationships
    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (Index("uq_workspaces_slug_lower", func.lower(slug), unique=True),)


class WorkspaceMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Membership junction associating users with workspaces and roles."""

    __tablename__ = "workspace_memberships"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="member",
        nullable=False,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="memberships",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
        lazy="selectin",
    )

    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),)
