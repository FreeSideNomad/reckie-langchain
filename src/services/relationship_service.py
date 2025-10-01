"""
RelationshipService for managing document relationships.

Provides CRUD operations and validation for document relationships:
- Create relationships with validation
- Read relationships (single, by parent, by child)
- Update relationship types
- Delete relationships
- Validate circular dependencies
- Validate parent-child type compatibility
- Hierarchy traversal (ancestors, descendants)
- Breadcrumb generation
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

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

    def get_ancestors(
        self, document_id: uuid.UUID, max_depth: int = 10
    ) -> List[Tuple[Document, str, int]]:
        """
        Get all ancestor documents using recursive CTE.

        Returns ancestors ordered from immediate parent to root.
        Example: User Story → Epic → Feature → Vision

        Args:
            document_id: Document UUID to get ancestors for
            max_depth: Maximum depth to traverse (default: 10)

        Returns:
            List of tuples: (Document, relationship_type, depth)
            where depth=1 is immediate parent, depth=2 is grandparent, etc.

        Example:
            ancestors = service.get_ancestors(story_id)
            for doc, rel_type, depth in ancestors:
                print(f"Depth {depth}: {doc.title} ({rel_type})")
        """
        # Convert UUID to string without dashes for SQLite compatibility
        doc_id_str = str(document_id).replace("-", "")

        query = text(
            """
            WITH RECURSIVE ancestors AS (
                -- Base case: immediate parents
                SELECT parent_id, child_id, relationship_type, 1 as depth
                FROM document_relationships
                WHERE child_id = :document_id

                UNION ALL

                -- Recursive case: parents of parents
                SELECT dr.parent_id, dr.child_id, dr.relationship_type, a.depth + 1
                FROM document_relationships dr
                INNER JOIN ancestors a ON dr.child_id = a.parent_id
                WHERE a.depth < :max_depth
            )
            SELECT parent_id, relationship_type, depth
            FROM ancestors
            ORDER BY depth
        """
        )

        result = self.db.execute(query, {"document_id": doc_id_str, "max_depth": max_depth})
        rows = result.fetchall()

        # Fetch Document objects for each parent_id
        ancestors = []
        for row in rows:
            parent_id_str = row[0]
            # Convert back to UUID format (add dashes)
            if len(parent_id_str) == 32:  # UUID without dashes
                parent_id_formatted = (
                    f"{parent_id_str[:8]}-{parent_id_str[8:12]}-"
                    f"{parent_id_str[12:16]}-{parent_id_str[16:20]}-{parent_id_str[20:]}"
                )
                parent_uuid = uuid.UUID(parent_id_formatted)
            else:
                parent_uuid = uuid.UUID(parent_id_str)

            parent_doc = self.db.query(Document).filter(Document.id == parent_uuid).first()
            if parent_doc:
                relationship_type = row[1]
                depth = row[2]
                ancestors.append((parent_doc, relationship_type, depth))

        return ancestors

    def get_descendants(
        self, document_id: uuid.UUID, max_depth: Optional[int] = None
    ) -> List[Tuple[Document, str, int]]:
        """
        Get all descendant documents using recursive CTE.

        Returns descendants in breadth-first order.
        Example: Vision → [F1, F2, F3] → [F1-E1, F1-E2, F2-E1, ...]

        Args:
            document_id: Document UUID to get descendants for
            max_depth: Maximum depth to traverse (None = unlimited, 1 = immediate children)

        Returns:
            List of tuples: (Document, relationship_type, depth)
            where depth=1 is immediate children, depth=2 is grandchildren, etc.

        Example:
            # Get immediate children only
            children = service.get_descendants(vision_id, max_depth=1)

            # Get all descendants
            all_descendants = service.get_descendants(vision_id)
        """
        # Convert UUID to string without dashes for SQLite compatibility
        doc_id_str = str(document_id).replace("-", "")

        # Set default max_depth to 20 if not specified
        if max_depth is None:
            max_depth = 20

        query = text(
            """
            WITH RECURSIVE descendants AS (
                -- Base case: immediate children
                SELECT parent_id, child_id, relationship_type, 1 as depth
                FROM document_relationships
                WHERE parent_id = :document_id

                UNION ALL

                -- Recursive case: children of children
                SELECT dr.parent_id, dr.child_id, dr.relationship_type, d.depth + 1
                FROM document_relationships dr
                INNER JOIN descendants d ON dr.parent_id = d.child_id
                WHERE d.depth < :max_depth
            )
            SELECT child_id, relationship_type, depth
            FROM descendants
            ORDER BY depth, child_id
        """
        )

        result = self.db.execute(query, {"document_id": doc_id_str, "max_depth": max_depth})
        rows = result.fetchall()

        # Fetch Document objects for each child_id
        descendants = []
        for row in rows:
            child_id_str = row[0]
            # Convert back to UUID format (add dashes)
            if len(child_id_str) == 32:  # UUID without dashes
                child_id_formatted = (
                    f"{child_id_str[:8]}-{child_id_str[8:12]}-"
                    f"{child_id_str[12:16]}-{child_id_str[16:20]}-{child_id_str[20:]}"
                )
                child_uuid = uuid.UUID(child_id_formatted)
            else:
                child_uuid = uuid.UUID(child_id_str)

            child_doc = self.db.query(Document).filter(Document.id == child_uuid).first()
            if child_doc:
                relationship_type = row[1]
                depth = row[2]
                descendants.append((child_doc, relationship_type, depth))

        return descendants

    def get_breadcrumb(
        self, document_id: uuid.UUID, separator: str = " > ", include_ids: bool = False
    ) -> str:
        """
        Generate navigation breadcrumb for a document.

        Creates a path from root to current document.
        Format: "Vision > Feature F1 > Epic F1-E1 > US-F1-E1-S1"

        Args:
            document_id: Document UUID to generate breadcrumb for
            separator: String to separate breadcrumb items (default: " > ")
            include_ids: Include document IDs in breadcrumb (default: False)

        Returns:
            Breadcrumb string

        Example:
            breadcrumb = service.get_breadcrumb(story_id)
            # Returns: "Test Vision > Test Feature > Test Epic > Test Story"

            breadcrumb_with_ids = service.get_breadcrumb(story_id, include_ids=True)
            # Returns: "Test Vision [abc...] > Test Feature [def...] > ..."
        """
        # Get current document
        current = self.db.query(Document).filter(Document.id == document_id).first()
        if not current:
            return ""

        # Get all ancestors
        ancestors = self.get_ancestors(document_id)

        # Build breadcrumb from root to current
        # Ancestors are ordered from immediate parent to root, so reverse them
        breadcrumb_parts = []

        # Add ancestors in reverse order (root first)
        for doc, _, _ in reversed(ancestors):
            if include_ids:
                breadcrumb_parts.append(f"{doc.title} [{str(doc.id)[:8]}]")
            else:
                breadcrumb_parts.append(doc.title)

        # Add current document
        if include_ids:
            breadcrumb_parts.append(f"{current.title} [{str(current.id)[:8]}]")
        else:
            breadcrumb_parts.append(current.title)

        return separator.join(breadcrumb_parts)

    def get_breadcrumb_with_details(self, document_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Generate breadcrumb with full document details for linking.

        Returns structured data suitable for rendering as clickable breadcrumb links.

        Args:
            document_id: Document UUID to generate breadcrumb for

        Returns:
            List of dicts with keys: id, title, document_type,
            relationship_type

        Example:
            breadcrumb = service.get_breadcrumb_with_details(story_id)
            # Returns: [
            #   {"id": "...", "title": "Vision",
            #    "document_type": "vision_document",
            #    "relationship_type": None},
            #   {"id": "...", "title": "Feature",
            #    "document_type": "feature_document",
            #    "relationship_type": "parent_child"},
            #   ...
            # ]
        """
        # Get current document
        current = self.db.query(Document).filter(Document.id == document_id).first()
        if not current:
            return []

        # Get all ancestors
        ancestors = self.get_ancestors(document_id)

        # Build breadcrumb list
        breadcrumb_items: List[Dict[str, Any]] = []

        # Add ancestors in reverse order (root first)
        for doc, rel_type, _ in reversed(ancestors):
            breadcrumb_items.append(
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "document_type": doc.document_type,
                    "relationship_type": rel_type,
                }
            )

        # Add current document (no relationship type for current)
        breadcrumb_items.append(
            {
                "id": str(current.id),
                "title": current.title,
                "document_type": current.document_type,
                "relationship_type": None,
            }
        )

        return breadcrumb_items

    def mark_descendants_for_review(
        self, document_id: uuid.UUID, max_depth: Optional[int] = None
    ) -> int:
        """
        Mark all descendant documents for review after parent change.

        When a parent document changes, all descendants should be reviewed
        to ensure consistency.

        Args:
            document_id: Parent document UUID that changed
            max_depth: Maximum depth to propagate (None = unlimited)

        Returns:
            Number of descendants marked for review

        Example:
            count = service.mark_descendants_for_review(vision_id)
            # Returns: 15 (all features, epics, stories marked)
        """
        from datetime import datetime, timezone

        # Get all descendants
        descendants = self.get_descendants(document_id, max_depth=max_depth)

        # Mark each descendant
        marked_count = 0
        for doc, _, depth in descendants:
            # Update metadata
            if doc.doc_metadata is None:
                doc.doc_metadata = {}

            doc.doc_metadata["needs_review"] = True
            doc.doc_metadata["parent_changed"] = {
                "parent_id": str(document_id),
                "changed_at": datetime.now(timezone.utc).isoformat(),
                "depth_from_changed": depth,
            }

            # Mark the JSONB field as modified
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(doc, "doc_metadata")

            marked_count += 1

        # Commit changes
        self.db.commit()

        return marked_count

    def get_parent_context(self, document_id: uuid.UUID, max_chars_per_parent: int = 2000) -> str:
        """
        Aggregate parent document context for RAG.

        Retrieves all ancestor documents and formats their content
        for use as context in LLM prompts.

        Args:
            document_id: Document UUID to get context for
            max_chars_per_parent: Maximum characters per parent (default: 2000)

        Returns:
            Formatted markdown string with parent context

        Example:
            context = service.get_parent_context(story_id)
            # Returns:
            # # Parent Context
            #
            # ## Vision: Product Roadmap 2024
            # Our vision is to...
            #
            # ## Feature: User Authentication
            # This feature will provide...
            #
            # ## Epic: Social Login
            # Users should be able to...
        """
        # Get all ancestors
        ancestors = self.get_ancestors(document_id)

        if not ancestors:
            return ""

        # Build context from root to immediate parent
        context_parts = ["# Parent Context\n"]

        for doc, _, _depth in reversed(ancestors):  # Root first
            # Add section for this parent
            context_parts.append(f"## {doc.document_type}: {doc.title}\n")

            # Get content (truncate if needed)
            content = doc.content_markdown or ""
            if len(content) > max_chars_per_parent:
                content = content[:max_chars_per_parent] + "\n\n[...truncated]"

            context_parts.append(content)
            context_parts.append("\n")  # Spacing between parents

        return "\n".join(context_parts)
