"""
DocumentRelationship model for tracking hierarchical relationships between documents.

Stores parent-child relationships and other relationship types:
- parent_child: Standard hierarchical relationship
- reference: Document references another document
- derived_from: Document derived from another

Supports recursive queries for:
- Getting all ancestors
- Getting all descendants
- Building breadcrumbs
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.document import Document


class DocumentRelationship(Base, TimestampMixin):
    """
    DocumentRelationship model for tracking relationships between documents.

    Attributes:
        id: UUID primary key
        parent_id: Parent document UUID
        child_id: Child document UUID
        relationship_type: Type of relationship (parent_child, reference, derived_from)
        created_at: Creation timestamp
        parent: Parent Document object
        child: Child Document object
    """

    __tablename__ = "document_relationships"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key generated on insert",
    )

    # Foreign Keys
    parent_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document ID",
    )

    child_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Child document ID",
    )

    # Relationship Type
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="parent_child",
        index=True,
        comment="Type of relationship: parent_child, reference, derived_from",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("parent_id", "child_id", name="uq_parent_child"),
        CheckConstraint("parent_id != child_id", name="chk_no_self_reference"),
    )

    # Relationships
    parent: Mapped["Document"] = relationship(
        "Document", foreign_keys=[parent_id], back_populates="child_relationships"
    )

    child: Mapped["Document"] = relationship(
        "Document", foreign_keys=[child_id], back_populates="parent_relationships"
    )

    # Validators
    @validates("relationship_type")
    def validate_relationship_type(self, key: str, relationship_type: str) -> str:
        """
        Validate relationship_type is in allowed list.

        Args:
            key: Field name
            relationship_type: Relationship type to validate

        Returns:
            Validated relationship type

        Raises:
            ValueError: If relationship type is not in allowed list
        """
        allowed_types = ["parent_child", "reference", "derived_from"]
        if relationship_type not in allowed_types:
            raise ValueError(
                f"Invalid relationship_type: {relationship_type}. "
                f"Must be one of {allowed_types}"
            )
        return relationship_type

    def __repr__(self) -> str:
        """String representation showing relationship details."""
        return (
            f"DocumentRelationship(id={self.id}, "
            f"type='{self.relationship_type}', "
            f"parent_id={self.parent_id}, child_id={self.child_id})"
        )
