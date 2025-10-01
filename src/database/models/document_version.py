"""
DocumentVersion model for version history snapshots.

Stores complete snapshots of documents for version control:
- Content snapshots (markdown and domain model)
- Audit trail (who changed, when, why)
- Version numbering (1, 2, 3, ...)
"""

import uuid
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, UniqueConstraint, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.database.base import Base

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")

if TYPE_CHECKING:
    from src.database.models.document import Document
    from src.database.models.user import User


class DocumentVersion(Base):
    """
    DocumentVersion model for storing version history snapshots.

    Attributes:
        id: UUID primary key
        document_id: Document being versioned
        version: Version number (1, 2, 3, ...)
        content_markdown: Snapshot of markdown content
        domain_model: Snapshot of domain model as JSONB
        changed_by: User who made the change
        changed_at: When the change was made
        change_description: Description of what changed
        document: Document object
        user: User who made the change
    """

    __tablename__ = "document_versions"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key generated on insert"
    )

    # Foreign Keys
    document_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Document being versioned"
    )

    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who made the change"
    )

    # Version Data
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Version number (1, 2, 3, ...)"
    )

    content_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Snapshot of markdown content"
    )

    domain_model: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        comment="Snapshot of domain model as JSONB"
    )

    # Audit Fields
    changed_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.now,
        comment="When the change was made"
    )

    change_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of what changed"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_version"),
        CheckConstraint("version > 0", name="chk_version_positive"),
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        foreign_keys=[document_id],
        back_populates="versions"
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[changed_by]
    )

    # Validators
    @validates("version")
    def validate_version(self, key: str, version: int) -> int:
        """
        Validate version is a positive integer.

        Args:
            key: Field name
            version: Version number to validate

        Returns:
            Validated version

        Raises:
            ValueError: If version is not positive
        """
        if version < 1:
            raise ValueError(f"Version must be >= 1, got {version}")
        return version

    def get_domain_model_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from domain_model JSONB snapshot.

        Args:
            key: Domain model key
            default: Default value if key not found

        Returns:
            Domain model value or default
        """
        if isinstance(self.domain_model, dict):
            return self.domain_model.get(key, default)
        return default

    def __repr__(self) -> str:
        """String representation showing version details."""
        return (
            f"DocumentVersion(id={self.id}, "
            f"document_id={self.document_id}, "
            f"version={self.version}, "
            f"changed_at={self.changed_at.isoformat() if self.changed_at else None})"
        )
