"""
DocumentType model for document type configuration.

Stores configuration for all 9 document types:
- research_report, business_context, vision_document
- feature_document, epic_document, user_story
- ddd_design, testing_strategy, test_plan

Each type defines:
- System prompts for AI conversations
- Workflow steps (JSONB array)
- Parent document types allowed
- Allowed personas (who can create this type)
- Additional configuration
"""

from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.database.base import Base, TimestampMixin

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")

if TYPE_CHECKING:
    from src.database.models.document import Document


class DocumentType(Base, TimestampMixin):
    """
    DocumentType model for storing document type configurations.

    Attributes:
        id: Auto-increment primary key
        type_name: Unique document type name
        system_prompt: AI system prompt for this document type
        workflow_steps: JSONB array of workflow step definitions
        parent_types: JSONB array of allowed parent document types
        allowed_personas: JSONB array of personas that can create this type
        config: JSONB object for additional configuration
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        documents: List of documents of this type
    """

    __tablename__ = "document_types"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Auto-increment primary key"
    )

    # Document Type Configuration
    type_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique document type name (e.g., vision_document, user_story)",
    )

    system_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="AI system prompt for conversations about this document type"
    )

    workflow_steps: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=list, comment="JSONB array of workflow step definitions"
    )

    parent_types: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, default=list, comment="JSONB array of allowed parent document types"
    )

    allowed_personas: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, default=list, comment="JSONB array of personas that can create this document type"
    )

    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, default=dict, comment="JSONB object for additional type-specific configuration"
    )

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="type", foreign_keys="[Document.document_type]"
    )

    # Hybrid Properties
    @hybrid_property
    def workflow_step_count(self) -> int:
        """
        Get number of workflow steps.

        Returns:
            Number of steps in workflow_steps array
        """
        if isinstance(self.workflow_steps, list):
            return len(self.workflow_steps)
        return 0

    @hybrid_property
    def parent_type_list(self) -> List[str]:
        """
        Get parent types as a Python list.

        Returns:
            List of parent document type names
        """
        if isinstance(self.parent_types, list):
            return self.parent_types
        return []

    @hybrid_property
    def allowed_persona_list(self) -> List[str]:
        """
        Get allowed personas as a Python list.

        Returns:
            List of persona names that can create this document type
        """
        if isinstance(self.allowed_personas, list):
            return self.allowed_personas
        return []

    # Validators
    @validates("type_name")
    def validate_type_name(self, key: str, type_name: str) -> str:
        """
        Validate type_name format (lowercase with underscores).

        Args:
            key: Field name
            type_name: Type name to validate

        Returns:
            Validated type name

        Raises:
            ValueError: If type name contains invalid characters
        """
        # Convert to lowercase and replace spaces with underscores
        type_name = type_name.lower().replace(" ", "_")

        # Ensure only alphanumeric and underscores
        if not all(c.isalnum() or c == "_" for c in type_name):
            raise ValueError(
                f"Invalid type_name: {type_name}. "
                "Must contain only letters, numbers, and underscores"
            )

        return type_name

    @validates("workflow_steps")
    def validate_workflow_steps(self, key: str, steps: Any) -> Any:
        """
        Validate workflow_steps is a list.

        Args:
            key: Field name
            steps: Workflow steps to validate

        Returns:
            Validated workflow steps

        Raises:
            ValueError: If steps is not a list
        """
        if steps is not None and not isinstance(steps, list):
            raise ValueError("workflow_steps must be a list")
        return steps or []

    def get_workflow_step(self, step_id: str) -> Dict[str, Any]:
        """
        Get a specific workflow step by ID.

        Args:
            step_id: ID of the workflow step

        Returns:
            Workflow step dictionary

        Raises:
            ValueError: If step_id not found
        """
        if not isinstance(self.workflow_steps, list):
            raise ValueError("workflow_steps is not a list")

        for step in self.workflow_steps:
            if isinstance(step, dict) and step.get("step_id") == step_id:
                return step

        raise ValueError(f"Workflow step '{step_id}' not found")

    def is_parent_allowed(self, parent_type_name: str) -> bool:
        """
        Check if a parent document type is allowed.

        Args:
            parent_type_name: Parent document type name to check

        Returns:
            True if parent type is allowed, False otherwise
        """
        return parent_type_name in self.parent_type_list

    def is_persona_allowed(self, persona: str) -> bool:
        """
        Check if a persona is allowed to create this document type.

        Args:
            persona: Persona name to check

        Returns:
            True if persona is allowed, False otherwise
        """
        return persona in self.allowed_persona_list

    def __repr__(self) -> str:
        """String representation showing type name and step count."""
        return (
            f"DocumentType(id={self.id}, type_name='{self.type_name}', "
            f"steps={self.workflow_step_count})"
        )
