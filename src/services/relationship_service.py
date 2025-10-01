"""
RelationshipService for managing document relationships.

Provides CRUD operations and validation for document relationships:
- Create relationships with validation
- Read relationships (single, by parent, by child)
- Update relationship types
- Delete relationships
- Validate circular dependencies
- Validate parent-child type compatibility
"""

import uuid
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import Document, DocumentRelationship, DocumentType


class RelationshipService:
    """
    Service for managing document relationships.

    Handles:
    - Creating relationships with validation (circular dependency, allowed parents)
    - Reading relationships (get by ID, by parent, by child)
    - Updating relationship types
    - Deleting relationships
    - Bulk operations

    Attributes:
        db: SQLAlchemy database session
    """

    def __init__(self, db: Session):
        """
        Initialize RelationshipService with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_relationship(
        self,
        parent_id: uuid.UUID,
        child_id: uuid.UUID,
        relationship_type: str = "parent_child",
    ) -> DocumentRelationship:
        """
        Create and validate document relationship.

        Validates:
        - Parent and child documents exist
        - Relationship type is allowed
        - Parent document type is in child's allowed parent types
        - No circular dependency exists
        - No self-referencing
        - No duplicate relationship

        Args:
            parent_id: Parent document UUID
            child_id: Child document UUID
            relationship_type: Type of relationship (default: parent_child)

        Returns:
            Created DocumentRelationship object

        Raises:
            ValueError: If validation fails
            IntegrityError: If database constraint violated
        """
        # Validate documents exist
        parent = self.db.query(Document).filter(Document.id == parent_id).first()
        child = self.db.query(Document).filter(Document.id == child_id).first()

        if not parent:
            raise ValueError(f"Parent document not found: {parent_id}")
        if not child:
            raise ValueError(f"Child document not found: {child_id}")

        # Validate no self-referencing
        if parent_id == child_id:
            raise ValueError("Cannot create self-referencing relationship")

        # Validate relationship is allowed by document type configuration
        if not self._is_relationship_allowed(parent.document_type, child.document_type):
            raise ValueError(
                f"Relationship not allowed: {child.document_type} "
                f"cannot have {parent.document_type} as parent"
            )

        # Check for circular dependency
        if self._creates_circular_dependency(parent_id, child_id):
            raise ValueError(
                f"Circular dependency detected: creating relationship from "
                f"{parent_id} to {child_id} would create a cycle"
            )

        # Check for duplicate relationship
        existing = (
            self.db.query(DocumentRelationship)
            .filter(
                DocumentRelationship.parent_id == parent_id,
                DocumentRelationship.child_id == child_id,
            )
            .first()
        )
        if existing:
            raise ValueError(
                f"Relationship already exists between parent {parent_id} " f"and child {child_id}"
            )

        # Create relationship
        try:
            relationship = DocumentRelationship(
                parent_id=parent_id, child_id=child_id, relationship_type=relationship_type
            )
            self.db.add(relationship)
            self.db.commit()
            self.db.refresh(relationship)
            return relationship
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")

    def get_relationship(self, relationship_id: uuid.UUID) -> Optional[DocumentRelationship]:
        """
        Get relationship by ID.

        Args:
            relationship_id: Relationship UUID

        Returns:
            DocumentRelationship object or None if not found
        """
        return (
            self.db.query(DocumentRelationship)
            .filter(DocumentRelationship.id == relationship_id)
            .first()
        )

    def get_relationships_by_parent(self, parent_id: uuid.UUID) -> List[DocumentRelationship]:
        """
        Get all relationships where document is parent.

        Args:
            parent_id: Parent document UUID

        Returns:
            List of DocumentRelationship objects
        """
        return (
            self.db.query(DocumentRelationship)
            .filter(DocumentRelationship.parent_id == parent_id)
            .all()
        )

    def get_relationships_by_child(self, child_id: uuid.UUID) -> List[DocumentRelationship]:
        """
        Get all relationships where document is child.

        Args:
            child_id: Child document UUID

        Returns:
            List of DocumentRelationship objects
        """
        return (
            self.db.query(DocumentRelationship)
            .filter(DocumentRelationship.child_id == child_id)
            .all()
        )

    def update_relationship_type(
        self, relationship_id: uuid.UUID, new_type: str
    ) -> DocumentRelationship:
        """
        Update relationship type.

        Args:
            relationship_id: Relationship UUID
            new_type: New relationship type

        Returns:
            Updated DocumentRelationship object

        Raises:
            ValueError: If relationship not found or invalid type
        """
        relationship = self.get_relationship(relationship_id)
        if not relationship:
            raise ValueError(f"Relationship not found: {relationship_id}")

        # Validator on model will check if type is valid
        try:
            relationship.relationship_type = new_type
            self.db.commit()
            self.db.refresh(relationship)
            return relationship
        except ValueError as e:
            self.db.rollback()
            raise ValueError(f"Invalid relationship type: {str(e)}")

    def delete_relationship(self, relationship_id: uuid.UUID) -> bool:
        """
        Delete relationship by ID.

        Args:
            relationship_id: Relationship UUID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If deletion fails
        """
        relationship = self.get_relationship(relationship_id)
        if not relationship:
            return False

        try:
            self.db.delete(relationship)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to delete relationship: {str(e)}")

    def create_bulk_relationships(self, relationships: List[dict]) -> List[DocumentRelationship]:
        """
        Create multiple relationships in a transaction.

        All relationships are validated before any are created.
        If any validation fails, no relationships are created.

        Args:
            relationships: List of dicts with keys: parent_id, child_id, relationship_type

        Returns:
            List of created DocumentRelationship objects

        Raises:
            ValueError: If any validation fails

        Example:
            relationships = [
                {"parent_id": uuid1, "child_id": uuid2, "relationship_type": "parent_child"},
                {"parent_id": uuid1, "child_id": uuid3},
            ]
        """
        # First pass: validate all relationships without creating
        for i, rel_data in enumerate(relationships):
            parent_id = rel_data["parent_id"]
            child_id = rel_data["child_id"]
            rel_type = rel_data.get("relationship_type", "parent_child")

            # Validate documents exist
            parent = self.db.query(Document).filter(Document.id == parent_id).first()
            child = self.db.query(Document).filter(Document.id == child_id).first()

            if not parent:
                raise ValueError(f"Relationship {i}: Parent document not found: {parent_id}")
            if not child:
                raise ValueError(f"Relationship {i}: Child document not found: {child_id}")

            # Validate no self-referencing
            if parent_id == child_id:
                raise ValueError(f"Relationship {i}: Cannot create self-referencing relationship")

            # Validate relationship is allowed
            if not self._is_relationship_allowed(parent.document_type, child.document_type):
                raise ValueError(
                    f"Relationship {i}: {child.document_type} "
                    f"cannot have {parent.document_type} as parent"
                )

            # Check for circular dependency
            if self._creates_circular_dependency(parent_id, child_id):
                raise ValueError(
                    f"Relationship {i}: Creating relationship from "
                    f"{parent_id} to {child_id} would create a cycle"
                )

        # Second pass: create all relationships
        created = []
        try:
            for rel_data in relationships:
                parent_id = rel_data["parent_id"]
                child_id = rel_data["child_id"]
                rel_type = rel_data.get("relationship_type", "parent_child")

                relationship = DocumentRelationship(
                    parent_id=parent_id, child_id=child_id, relationship_type=rel_type
                )
                self.db.add(relationship)
                created.append(relationship)

            self.db.commit()

            # Refresh all created relationships
            for rel in created:
                self.db.refresh(rel)

            return created

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Bulk relationship creation failed: {str(e)}")

    def _is_relationship_allowed(self, parent_type: str, child_type: str) -> bool:
        """
        Check if relationship is allowed based on document type configuration.

        Args:
            parent_type: Parent document type name
            child_type: Child document type name

        Returns:
            True if relationship is allowed, False otherwise
        """
        # Get child document type configuration
        child_doc_type = (
            self.db.query(DocumentType).filter(DocumentType.type_name == child_type).first()
        )

        if not child_doc_type:
            # If child document type not found, allow relationship
            # (type validation should happen elsewhere)
            return True

        # Check if parent type is in child's allowed parent types
        return child_doc_type.is_parent_allowed(parent_type)

    def _creates_circular_dependency(self, parent_id: uuid.UUID, child_id: uuid.UUID) -> bool:
        """
        Check if creating this relationship would create a circular dependency.

        We want to create: parent_id -> child_id
        This creates a cycle if parent_id is a descendant of child_id.
        In other words, if there's already a path: child_id -> ... -> parent_id

        Args:
            parent_id: Proposed parent document UUID
            child_id: Proposed child document UUID

        Returns:
            True if circular dependency would be created, False otherwise
        """
        # Check if parent_id is already a descendant of child_id
        # We do this by finding all descendants of child_id and seeing if parent_id is among them
        query = text(
            """
            WITH RECURSIVE descendants AS (
                -- Base case: immediate children of child_id
                SELECT parent_id, child_id, 1 as depth
                FROM document_relationships
                WHERE parent_id = :child_id

                UNION ALL

                -- Recursive case: children of children
                SELECT dr.parent_id, dr.child_id, d.depth + 1
                FROM document_relationships dr
                INNER JOIN descendants d ON dr.parent_id = d.child_id
                WHERE d.depth < 20  -- Prevent infinite loops
            )
            SELECT COUNT(*) as count
            FROM descendants
            WHERE child_id = :parent_id
        """
        )

        # Convert UUIDs to strings for compatibility with SQLite
        # Note: SQLite stores UUIDs without dashes, so we need to remove them
        child_id_str = str(child_id).replace("-", "")
        parent_id_str = str(parent_id).replace("-", "")

        result = self.db.execute(query, {"child_id": child_id_str, "parent_id": parent_id_str})
        row = result.fetchone()
        count = row[0] if row else 0

        return count > 0
