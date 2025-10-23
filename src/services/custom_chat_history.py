"""Custom chat message history implementation for conversations table.

Implements LangChain's BaseChatMessageHistory to work with the conversations
table schema (user_id, document_id, history JSONB).
"""

import json
from typing import List, Optional
from uuid import UUID

from langchain.schema import BaseChatMessageHistory
from langchain.schema.messages import BaseMessage, messages_from_dict, messages_to_dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


class ConversationsChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in conversations table.

    Uses the conversations table schema:
    - id: UUID (primary key)
    - user_id: UUID (foreign key to users)
    - document_id: UUID (foreign key to documents)
    - history: JSONB (array of messages)
    - state: JSONB (additional state)
    - created_at: timestamp
    - updated_at: timestamp
    """

    def __init__(
        self,
        conversation_id: UUID,
        user_id: UUID,
        document_id: UUID,
        connection_string: str,
    ):
        """Initialize conversation history.

        Args:
            conversation_id: Unique conversation ID
            user_id: User UUID
            document_id: Document UUID being edited
            connection_string: PostgreSQL connection string
        """
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.document_id = document_id
        self.engine = create_engine(connection_string)

        # Ensure conversation record exists
        self._ensure_conversation_exists()

    def _ensure_conversation_exists(self) -> None:
        """Create conversation record if it doesn't exist."""
        with Session(self.engine) as session:
            # Use ON CONFLICT on the unique constraint (user_id, document_id)
            # to handle the case where a conversation already exists for this user+document
            session.execute(
                text("""
                    INSERT INTO conversations (id, user_id, document_id, history, state)
                    VALUES (:id, :user_id, :document_id, '[]'::jsonb, '{}'::jsonb)
                    ON CONFLICT (user_id, document_id) DO UPDATE
                    SET id = :id
                """),
                {
                    "id": str(self.conversation_id),
                    "user_id": str(self.user_id),
                    "document_id": str(self.document_id),
                }
            )
            session.commit()

    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve messages from conversations.history JSONB column."""
        with Session(self.engine) as session:
            result = session.execute(
                text("SELECT history FROM conversations WHERE id = :id"),
                {"id": str(self.conversation_id)}
            ).fetchone()

            if result is None:
                return []

            history_json = result[0]  # JSONB column

            if not history_json:
                return []

            # Convert JSONB array to LangChain messages
            return messages_from_dict(history_json)

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to conversations.history JSONB array."""
        with Session(self.engine) as session:
            # Get current history
            result = session.execute(
                text("SELECT history FROM conversations WHERE id = :id"),
                {"id": str(self.conversation_id)}
            ).fetchone()

            current_history = result[0] if result else []

            # Convert message to dict and append
            message_dict = messages_to_dict([message])[0]
            current_history.append(message_dict)

            # Update database with new history (convert to JSON string)
            session.execute(
                text("""
                    UPDATE conversations
                    SET history = CAST(:history AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": str(self.conversation_id),
                    "history": json.dumps(current_history)
                }
            )
            session.commit()

    def clear(self) -> None:
        """Clear all messages from conversation history."""
        with Session(self.engine) as session:
            session.execute(
                text("""
                    UPDATE conversations
                    SET history = '[]'::jsonb,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": str(self.conversation_id)}
            )
            session.commit()

    def get_state(self) -> dict:
        """Get conversation state JSONB."""
        with Session(self.engine) as session:
            result = session.execute(
                text("SELECT state FROM conversations WHERE id = :id"),
                {"id": str(self.conversation_id)}
            ).fetchone()

            return result[0] if result else {}

    def update_state(self, state: dict) -> None:
        """Update conversation state JSONB."""
        with Session(self.engine) as session:
            session.execute(
                text("""
                    UPDATE conversations
                    SET state = CAST(:state AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": str(self.conversation_id),
                    "state": json.dumps(state)
                }
            )
            session.commit()
