"""Audit logging persistence model."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from askbase.models.base import Base, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable audit entry recording domain actions."""

    __tablename__ = "audit_logs"

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    @property
    def details(self) -> dict[str, Any] | None:
        """Parse details JSON payload."""
        if not self.details_json:
            return None
        try:
            val = json.loads(self.details_json)
            return dict(val) if isinstance(val, dict) else None
        except Exception:
            return None

    @details.setter
    def details(self, val: dict[str, Any] | None) -> None:
        """Serialize details payload to JSON."""
        if val is None:
            self.details_json = None
        else:
            self.details_json = json.dumps(val)

    __table_args__ = (Index("idx_audit_ws_time", "workspace_id", "created_at"),)
