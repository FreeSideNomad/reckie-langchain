"""
Conversation model for AI conversation history.

Stores conversation state and message history for multi-turn conversations:
- Message history with timestamps
- Workflow state tracking
- One conversation per user per document
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")

if TYPE_CHECKING:
    from src.database.models.document import Document
    from src.database.models.user import User


class Conversation(Base, TimestampMixin):
    """
    Conversation model for tracking AI conversation history.

    Attributes:
        id: UUID primary key
        user_id: User participating in conversation
        document_id: Document being discussed
        history: JSONB array of messages [{role, content, timestamp}]
        state: JSONB object for workflow state {current_step, turn_count, etc.}
        created_at: Conversation start timestamp
        updated_at: Last message timestamp
        user: User object
        document: Document object
    """

    __tablename__ = "conversations"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key generated on insert",
    )

    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User participating in conversation",
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Document being discussed",
    )

    # Conversation Data
    history: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONType, default=list, comment="JSONB array of messages: [{role, content, timestamp}]"
    )

    state: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        default=dict,
        comment="JSONB workflow state: {current_step, turn_count, started_at, workflow_data}",
    )

    # Constraints
    __table_args__ = (UniqueConstraint("user_id", "document_id", name="uq_user_document"),)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="conversations"
    )

    document: Mapped["Document"] = relationship(
        "Document", foreign_keys=[document_id], back_populates="conversations"
    )

    # Helper Methods
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        if not isinstance(self.history, list):
            self.history = []

        message = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        self.history.append(message)

    def get_current_step(self) -> Optional[str]:
        """
        Get current workflow step from state.

        Returns:
            Current step ID or None
        """
        if isinstance(self.state, dict):
            return self.state.get("current_step")
        return None

    def update_workflow_state(self, key: str, value: Any) -> None:
        """
        Update a value in workflow state.

        Args:
            key: State key
            value: Value to set
        """
        if not isinstance(self.state, dict):
            self.state = {}
        self.state[key] = value

    def get_message_count(self) -> int:
        """
        Get number of messages in conversation.

        Returns:
            Number of messages
        """
        if isinstance(self.history, list):
            return len(self.history)
        return 0

    def __repr__(self) -> str:
        """String representation showing conversation details."""
        message_count = self.get_message_count()
        return (
            f"Conversation(id={self.id}, "
            f"user_id={self.user_id}, "
            f"document_id={self.document_id}, "
            f"messages={message_count})"
        )
