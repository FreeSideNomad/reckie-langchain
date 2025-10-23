"""Conversation logger for recording and replaying CLI interactions."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID


@dataclass
class ConversationEntry:
    """Single conversation entry (user input + system response)."""
    timestamp: str
    entry_type: str  # "user_input" or "system_response"
    content: str
    metadata: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ConversationLog:
    """Complete conversation log."""
    log_id: str
    conversation_id: str
    user_id: str
    document_type: str
    started_at: str
    ended_at: Optional[str] = None
    entries: List[ConversationEntry] = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = []

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "log_id": self.log_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "document_type": self.document_type,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "entries": [entry.to_dict() for entry in self.entries]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationLog":
        """Create from dictionary (for loading from JSON)."""
        entries = [
            ConversationEntry(**entry)
            for entry in data.get("entries", [])
        ]
        return cls(
            log_id=data["log_id"],
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            document_type=data["document_type"],
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            entries=entries
        )


class ConversationLogger:
    """Manages conversation recording and replay."""

    def __init__(self, log_dir: str = "conversation-logs"):
        """Initialize logger.

        Args:
            log_dir: Directory to store conversation logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log: Optional[ConversationLog] = None
        self.recording = False

    def start_recording(
        self,
        conversation_id: UUID,
        user_id: UUID,
        document_type: str
    ) -> str:
        """Start recording a new conversation.

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            document_type: Type of document being created

        Returns:
            Log ID
        """
        timestamp = datetime.utcnow().isoformat()
        log_id = f"{document_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        self.current_log = ConversationLog(
            log_id=log_id,
            conversation_id=str(conversation_id),
            user_id=str(user_id),
            document_type=document_type,
            started_at=timestamp
        )
        self.recording = True

        return log_id

    def log_user_input(self, user_input: str, metadata: Optional[dict] = None):
        """Log user input.

        Args:
            user_input: User's input text
            metadata: Optional metadata (e.g., action type, context)
        """
        if not self.recording or not self.current_log:
            return

        entry = ConversationEntry(
            timestamp=datetime.utcnow().isoformat(),
            entry_type="user_input",
            content=user_input,
            metadata=metadata
        )
        self.current_log.entries.append(entry)

    def log_system_response(
        self,
        response: str,
        metadata: Optional[dict] = None
    ):
        """Log system response.

        Args:
            response: System's response text
            metadata: Optional metadata (e.g., action, workflow state)
        """
        if not self.recording or not self.current_log:
            return

        entry = ConversationEntry(
            timestamp=datetime.utcnow().isoformat(),
            entry_type="system_response",
            content=response,
            metadata=metadata
        )
        self.current_log.entries.append(entry)

    def stop_recording(self) -> Optional[str]:
        """Stop recording and save log to disk.

        Returns:
            Path to saved log file, or None if not recording
        """
        if not self.recording or not self.current_log:
            return None

        self.current_log.ended_at = datetime.utcnow().isoformat()
        self.recording = False

        # Save to file
        log_file = self.log_dir / f"{self.current_log.log_id}.json"
        with open(log_file, 'w') as f:
            json.dump(self.current_log.to_dict(), f, indent=2)

        return str(log_file)

    def list_logs(self) -> List[dict]:
        """List all available conversation logs.

        Returns:
            List of log summaries with metadata
        """
        logs = []

        for log_file in sorted(self.log_dir.glob("*.json")):
            try:
                with open(log_file, 'r') as f:
                    data = json.load(f)

                logs.append({
                    "file_name": log_file.name,
                    "file_path": str(log_file),
                    "log_id": data["log_id"],
                    "document_type": data["document_type"],
                    "started_at": data["started_at"],
                    "ended_at": data.get("ended_at"),
                    "entry_count": len(data.get("entries", []))
                })
            except Exception as e:
                # Skip corrupted files
                continue

        return logs

    def load_log(self, log_file_path: str) -> Optional[ConversationLog]:
        """Load a conversation log from disk.

        Args:
            log_file_path: Path to log file

        Returns:
            ConversationLog or None if not found
        """
        log_path = Path(log_file_path)

        if not log_path.exists():
            return None

        try:
            with open(log_path, 'r') as f:
                data = json.load(f)
            return ConversationLog.from_dict(data)
        except Exception:
            return None

    def get_user_inputs(self, log: ConversationLog) -> List[tuple]:
        """Extract user inputs from log for replay.

        Args:
            log: ConversationLog instance

        Returns:
            List of (user_input, metadata) tuples
        """
        return [
            (entry.content, entry.metadata)
            for entry in log.entries
            if entry.entry_type == "user_input"
        ]
