"""
Document model - central table for all document types.

Stores all documents in the system:
- Vision documents, Features, Epics, User Stories
- Research Reports, Business Context
- DDD Designs, Testing Strategy, Test Plans

Each document has:
- Markdown content (rendered output)
- JSONB domain model (structured data)
- JSONB metadata (tags, priority, etc.)
- Version tracking
- Status lifecycle (draft → in_progress → complete → stale)
- Relationships to other documents (parent-child hierarchy)
"""

import uuid
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.database.base import Base, TimestampMixin

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")

if TYPE_CHECKING:
    from src.database.models.user import User
    from src.database.models.document_type import DocumentType
    from src.database.models.document_relationship import DocumentRelationship
    from src.database.models.conversation import Conversation
    from src.database.models.document_version import DocumentVersion
    from src.database.models.document_embedding import DocumentEmbedding


class Document(Base, TimestampMixin):
    """
    Document model - central table storing all document types.

    Attributes:
        id: UUID primary key
        user_id: Owner of the document (foreign key to users)
        document_type: Type of document (foreign key to document_types)
        title: User-friendly document title
        content_markdown: Rendered markdown content (AI-generated)
        domain_model: YAML domain model as JSONB (structured data)
        metadata: Additional metadata as JSONB (tags, priority, etc.)
        version: Version number (incremented on changes)
        status: Document lifecycle status (draft, in_progress, complete, stale)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the document
        updated_by: User who last updated the document
        user: User who owns this document (relationship)
        type: DocumentType configuration (relationship)
        parent_relationships: Relationships where this is the child
        child_relationships: Relationships where this is the parent
        embeddings: Vector embeddings for RAG
        conversations: AI conversation history
        versions: Version history snapshots
    """

    __tablename__ = "documents"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key generated on insert"
    )

    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Document owner (foreign key to users)"
    )

    document_type: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("document_types.type_name"),
        nullable=False,
        index=True,
        comment="Document type (foreign key to document_types)"
    )

    # Document Content
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="User-friendly document title"
    )

    content_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Rendered markdown content (AI-generated)"
    )

    domain_model: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        comment="YAML domain model as JSONB (structured data)"
    )

    doc_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        comment="Additional metadata: tags, priority, story_points, sprint, etc."
    )

    # Version and Status
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Version number (incremented on changes)"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        index=True,
        comment="Document lifecycle status: draft, in_progress, complete, stale"
    )

    # Audit Fields
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who created document"
    )

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who last updated document"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="documents"
    )

    type: Mapped["DocumentType"] = relationship(
        "DocumentType",
        foreign_keys=[document_type],
        back_populates="documents"
    )

    parent_relationships: Mapped[List["DocumentRelationship"]] = relationship(
        "DocumentRelationship",
        foreign_keys="[DocumentRelationship.child_id]",
        back_populates="child",
        cascade="all, delete-orphan"
    )

    child_relationships: Mapped[List["DocumentRelationship"]] = relationship(
        "DocumentRelationship",
        foreign_keys="[DocumentRelationship.parent_id]",
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    embeddings: Mapped[List["DocumentEmbedding"]] = relationship(
        "DocumentEmbedding",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    # Validators
    @validates("status")
    def validate_status(self, key: str, status: str) -> str:
        """
        Validate status is in allowed list.

        Args:
            key: Field name
            status: Status to validate

        Returns:
            Validated status

        Raises:
            ValueError: If status is not in allowed list
        """
        allowed_statuses = ["draft", "in_progress", "complete", "stale"]
        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid status: {status}. Must be one of {allowed_statuses}"
            )
        return status

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

    # Helper Methods
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from doc_metadata JSONB.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        if isinstance(self.doc_metadata, dict):
            return self.doc_metadata.get(key, default)
        return default

    def set_metadata_value(self, key: str, value: Any) -> None:
        """
        Set a value in doc_metadata JSONB.

        Args:
            key: Metadata key
            value: Value to set
        """
        if not isinstance(self.doc_metadata, dict):
            self.doc_metadata = {}
        self.doc_metadata[key] = value

    def get_domain_model_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from domain_model JSONB.

        Args:
            key: Domain model key
            default: Default value if key not found

        Returns:
            Domain model value or default
        """
        if isinstance(self.domain_model, dict):
            return self.domain_model.get(key, default)
        return default

    def is_complete(self) -> bool:
        """Check if document is marked as complete."""
        return self.status == "complete"

    def is_draft(self) -> bool:
        """Check if document is still a draft."""
        return self.status == "draft"

    def mark_complete(self) -> None:
        """Mark document as complete."""
        self.status = "complete"

    def mark_stale(self) -> None:
        """Mark document as stale (parent changed, needs review)."""
        self.status = "stale"

    def increment_version(self) -> None:
        """Increment document version number."""
        self.version += 1

    def __repr__(self) -> str:
        """String representation showing title and type."""
        return f"Document(id={self.id}, title='{self.title}', type='{self.document_type}', status='{self.status}')"
