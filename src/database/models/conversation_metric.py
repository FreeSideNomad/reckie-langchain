"""ConversationMetric model for token tracking."""

import uuid

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from src.database.base import Base


class ConversationMetric(Base):
    """
    Token usage tracking per conversation turn.

    Records facts (model + tokens) for cost calculation in analytics layer.
    No hardcoded cost calculations - pricing determined externally.
    """

    __tablename__ = "conversation_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    model = Column(String(50), nullable=False, index=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Metadata for analytics and debugging
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_occurred = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ConversationMetric(id={self.id}, conversation_id={self.conversation_id}, "
            f"model={self.model}, total_tokens={self.total_tokens})>"
        )

    @property
    def has_error(self) -> bool:
        """Check if this metric recorded an error."""
        return bool(self.error_occurred)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "duration_ms": self.duration_ms,
            "error_occurred": self.error_occurred,
            "error_message": self.error_message,
        }
