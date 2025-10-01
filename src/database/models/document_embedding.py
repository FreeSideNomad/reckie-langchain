"""
DocumentEmbedding model for vector embeddings storage.

Stores vector embeddings for RAG-powered context retrieval:
- OpenAI text-embedding-3-small (1536 dimensions)
- Document chunking with index tracking
- Metadata for chunk information
- pgvector support for similarity search
"""

import uuid
from typing import Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Integer, ForeignKey, UniqueConstraint, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from pgvector.sqlalchemy import Vector

from src.database.base import Base, TimestampMixin

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")

if TYPE_CHECKING:
    from src.database.models.document import Document


class DocumentEmbedding(Base, TimestampMixin):
    """
    DocumentEmbedding model for storing vector embeddings.

    Attributes:
        id: UUID primary key
        document_id: Document being embedded
        chunk_text: Text content of chunk
        chunk_index: Index of chunk in document (0, 1, 2, ...)
        embedding: Vector embedding (1536 dimensions for OpenAI)
        metadata: JSONB for chunk metadata (tokens, context, etc.)
        created_at: Embedding creation timestamp
        document: Document object
    """

    __tablename__ = "document_embeddings"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key generated on insert"
    )

    # Foreign Key
    document_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Document being embedded"
    )

    # Chunk Data
    chunk_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Text content of chunk"
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Index of chunk in document (0, 1, 2, ...)"
    )

    # Vector Embedding
    # Note: For SQLite testing, we'll store as JSON array. For PostgreSQL, use Vector type.
    embedding: Mapped[Optional[str]] = mapped_column(
        Vector(1536) if __name__ != "__main__" else Text,
        nullable=True,
        comment="Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)"
    )

    # Metadata
    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        comment="JSONB for chunk metadata: tokens, context, overlap, etc."
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
        CheckConstraint("chunk_index >= 0", name="chk_chunk_index_positive"),
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        foreign_keys=[document_id],
        back_populates="embeddings"
    )

    # Validators
    @validates("chunk_index")
    def validate_chunk_index(self, key: str, chunk_index: int) -> int:
        """
        Validate chunk_index is non-negative.

        Args:
            key: Field name
            chunk_index: Chunk index to validate

        Returns:
            Validated chunk index

        Raises:
            ValueError: If chunk index is negative
        """
        if chunk_index < 0:
            raise ValueError(f"Chunk index must be >= 0, got {chunk_index}")
        return chunk_index

    @validates("chunk_text")
    def validate_chunk_text(self, key: str, chunk_text: str) -> str:
        """
        Validate chunk_text is not empty.

        Args:
            key: Field name
            chunk_text: Chunk text to validate

        Returns:
            Validated chunk text

        Raises:
            ValueError: If chunk text is empty
        """
        if not chunk_text or not chunk_text.strip():
            raise ValueError("Chunk text cannot be empty")
        return chunk_text

    # Helper Methods
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from chunk_metadata JSONB.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        if isinstance(self.chunk_metadata, dict):
            return self.chunk_metadata.get(key, default)
        return default

    def set_metadata_value(self, key: str, value: Any) -> None:
        """
        Set a value in chunk_metadata JSONB.

        Args:
            key: Metadata key
            value: Value to set
        """
        if not isinstance(self.chunk_metadata, dict):
            self.chunk_metadata = {}
        self.chunk_metadata[key] = value

    def get_embedding_dimension(self) -> int:
        """
        Get embedding vector dimension.

        Returns:
            Embedding dimension (1536 for OpenAI text-embedding-3-small)
        """
        return 1536

    def __repr__(self) -> str:
        """String representation showing embedding details."""
        return (
            f"DocumentEmbedding(id={self.id}, "
            f"document_id={self.document_id}, "
            f"chunk_index={self.chunk_index}, "
            f"text_preview='{self.chunk_text[:50]}...')"
        )
