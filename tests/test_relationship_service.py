"""
Unit tests for RelationshipService.

Tests all CRUD operations and validation logic for document relationships:
- Creating relationships with validation
- Reading relationships
- Updating relationship types
- Deleting relationships
- Circular dependency detection
- Parent type validation
- Bulk operations
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models import Document, DocumentType, User
from src.services.relationship_service import RelationshipService


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def service(db_session):
    """Create RelationshipService instance."""
    return RelationshipService(db_session)


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def document_types(db_session):
    """Create document types with parent type configuration."""
    # Vision document (no parents - root document)
    vision_type = DocumentType(
        type_name="vision_document",
        system_prompt="Vision document prompt",
        workflow_steps=[],
        parent_types=[],  # No parents allowed
        allowed_personas=["product_manager"],
    )

    # Feature document (parent: vision)
    feature_type = DocumentType(
        type_name="feature_document",
        system_prompt="Feature document prompt",
        workflow_steps=[],
        parent_types=["vision_document"],
        allowed_personas=["product_manager"],
    )

    # Epic document (parent: feature)
    epic_type = DocumentType(
        type_name="epic_document",
        system_prompt="Epic document prompt",
        workflow_steps=[],
        parent_types=["feature_document"],
        allowed_personas=["product_manager"],
    )

    # User story (parent: epic)
    story_type = DocumentType(
        type_name="user_story",
        system_prompt="User story prompt",
        workflow_steps=[],
        parent_types=["epic_document"],
        allowed_personas=["product_manager", "developer"],
    )

    db_session.add_all([vision_type, feature_type, epic_type, story_type])
    db_session.commit()

    return {
        "vision": vision_type,
        "feature": feature_type,
        "epic": epic_type,
        "story": story_type,
    }


@pytest.fixture
def test_documents(db_session, test_user, document_types):
    """Create test documents for relationship tests."""
    vision = Document(
        user_id=test_user.id,
        document_type="vision_document",
        title="Test Vision",
        content_markdown="# Test Vision",
        domain_model={},
        doc_metadata={},
    )

    feature = Document(
        user_id=test_user.id,
        document_type="feature_document",
        title="Test Feature",
        content_markdown="# Test Feature",
        domain_model={},
        doc_metadata={},
    )

    epic = Document(
        user_id=test_user.id,
        document_type="epic_document",
        title="Test Epic",
        content_markdown="# Test Epic",
        domain_model={},
        doc_metadata={},
    )

    story = Document(
        user_id=test_user.id,
        document_type="user_story",
        title="Test Story",
        content_markdown="# Test Story",
        domain_model={},
        doc_metadata={},
    )

    db_session.add_all([vision, feature, epic, story])
    db_session.commit()

    return {
        "vision": vision,
        "feature": feature,
        "epic": epic,
        "story": story,
    }


class TestRelationshipCreation:
    """Test relationship creation and validation."""

    def test_create_valid_relationship(self, service, test_documents):
        """Test creating a valid parent-child relationship."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]

        rel = service.create_relationship(
            parent_id=vision.id,
            child_id=feature.id,
            relationship_type="parent_child",
        )

        assert rel is not None
        assert rel.parent_id == vision.id
        assert rel.child_id == feature.id
        assert rel.relationship_type == "parent_child"
        assert isinstance(rel.id, uuid.UUID)

    def test_create_relationship_invalid_parent(self, service, test_documents):
        """Test creating relationship with non-existent parent."""
        feature = test_documents["feature"]
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Parent document not found"):
            service.create_relationship(
                parent_id=fake_id,
                child_id=feature.id,
            )

    def test_create_relationship_invalid_child(self, service, test_documents):
        """Test creating relationship with non-existent child."""
        vision = test_documents["vision"]
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Child document not found"):
            service.create_relationship(
                parent_id=vision.id,
                child_id=fake_id,
            )

    def test_create_self_referencing_relationship(self, service, test_documents):
        """Test that self-referencing relationships are rejected."""
        vision = test_documents["vision"]

        with pytest.raises(ValueError, match="self-referencing"):
            service.create_relationship(
                parent_id=vision.id,
                child_id=vision.id,
            )

    def test_create_relationship_wrong_parent_type(self, service, test_documents):
        """Test creating relationship with incompatible parent type."""
        # Try to make story a child of vision (should fail - story needs epic parent)
        vision = test_documents["vision"]
        story = test_documents["story"]

        with pytest.raises(ValueError, match="Relationship not allowed"):
            service.create_relationship(
                parent_id=vision.id,
                child_id=story.id,
            )

    def test_create_duplicate_relationship(self, service, test_documents):
        """Test that duplicate relationships are rejected."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]

        # Create first relationship
        service.create_relationship(
            parent_id=vision.id,
            child_id=feature.id,
        )

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            service.create_relationship(
                parent_id=vision.id,
                child_id=feature.id,
            )

    def test_create_circular_dependency(self, service, test_documents):
        """Test circular dependency detection."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]
        epic = test_documents["epic"]

        # Create chain: vision -> feature -> epic
        service.create_relationship(vision.id, feature.id)
        service.create_relationship(feature.id, epic.id)

        # Try to create epic -> feature (would create cycle)
        # This will fail with "Relationship not allowed" because epic_document
        # cannot have feature_document as parent (type validation runs first)
        with pytest.raises(ValueError, match="Relationship not allowed"):
            service.create_relationship(epic.id, feature.id)


class TestRelationshipRead:
    """Test reading relationship operations."""

    def test_get_relationship_by_id(self, service, test_documents):
        """Test getting relationship by ID."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]

        rel = service.create_relationship(vision.id, feature.id)
        fetched = service.get_relationship(rel.id)

        assert fetched is not None
        assert fetched.id == rel.id
        assert fetched.parent_id == vision.id
        assert fetched.child_id == feature.id

    def test_get_nonexistent_relationship(self, service):
        """Test getting relationship that doesn't exist."""
        fake_id = uuid.uuid4()
        result = service.get_relationship(fake_id)
        assert result is None

    def test_get_relationships_by_parent(self, service, test_documents):
        """Test getting all relationships where document is parent."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]
        epic = test_documents["epic"]

        # Create two relationships with vision as parent
        rel1 = service.create_relationship(vision.id, feature.id)
        service.create_relationship(feature.id, epic.id)  # Different parent

        relationships = service.get_relationships_by_parent(vision.id)

        assert len(relationships) == 1
        assert relationships[0].id == rel1.id
        assert relationships[0].parent_id == vision.id

    def test_get_relationships_by_child(self, service, test_documents):
        """Test getting all relationships where document is child."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]
        epic = test_documents["epic"]

        # Create relationships
        service.create_relationship(vision.id, feature.id)
        rel2 = service.create_relationship(feature.id, epic.id)

        relationships = service.get_relationships_by_child(epic.id)

        assert len(relationships) == 1
        assert relationships[0].id == rel2.id
        assert relationships[0].child_id == epic.id


class TestRelationshipUpdate:
    """Test relationship update operations."""

    def test_update_relationship_type(self, service, test_documents):
        """Test updating relationship type."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]

        rel = service.create_relationship(vision.id, feature.id, "parent_child")
        updated = service.update_relationship_type(rel.id, "reference")

        assert updated.relationship_type == "reference"

    def test_update_relationship_invalid_type(self, service, test_documents):
        """Test updating to invalid relationship type."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]

        rel = service.create_relationship(vision.id, feature.id)

        with pytest.raises(ValueError, match="Invalid relationship type"):
            service.update_relationship_type(rel.id, "invalid_type")

    def test_update_nonexistent_relationship(self, service):
        """Test updating relationship that doesn't exist."""
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            service.update_relationship_type(fake_id, "reference")


class TestRelationshipDelete:
    """Test relationship deletion operations."""

    def test_delete_relationship(self, service, test_documents):
        """Test deleting a relationship."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]

        rel = service.create_relationship(vision.id, feature.id)
        result = service.delete_relationship(rel.id)

        assert result is True
        assert service.get_relationship(rel.id) is None

    def test_delete_nonexistent_relationship(self, service):
        """Test deleting relationship that doesn't exist."""
        fake_id = uuid.uuid4()
        result = service.delete_relationship(fake_id)
        assert result is False


class TestBulkOperations:
    """Test bulk relationship operations."""

    def test_create_bulk_relationships_success(self, service, test_documents):
        """Test creating multiple relationships at once."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]
        epic = test_documents["epic"]
        story = test_documents["story"]

        relationships = [
            {"parent_id": vision.id, "child_id": feature.id},
            {"parent_id": feature.id, "child_id": epic.id},
            {"parent_id": epic.id, "child_id": story.id},
        ]

        created = service.create_bulk_relationships(relationships)

        assert len(created) == 3
        assert all(isinstance(rel.id, uuid.UUID) for rel in created)

        # Verify all were created
        assert service.get_relationship(created[0].id) is not None
        assert service.get_relationship(created[1].id) is not None
        assert service.get_relationship(created[2].id) is not None

    def test_create_bulk_relationships_with_failure(self, service, test_documents):
        """Test bulk creation fails if any relationship is invalid."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]
        fake_id = uuid.uuid4()

        relationships = [
            {"parent_id": vision.id, "child_id": feature.id},
            {"parent_id": fake_id, "child_id": feature.id},  # Invalid
        ]

        with pytest.raises(ValueError, match="Parent document not found"):
            service.create_bulk_relationships(relationships)

        # Verify nothing was created (validation failed before creation)
        all_rels = service.get_relationships_by_parent(vision.id)
        assert len(all_rels) == 0


class TestCircularDependencyDetection:
    """Test circular dependency detection edge cases."""

    def test_deep_circular_dependency(self, service, test_documents, db_session, test_user):
        """Test circular dependency detection in deep hierarchy."""
        # Create a custom document type that allows itself as parent for this test
        custom_type = DocumentType(
            type_name="custom_document",
            system_prompt="Custom document prompt",
            workflow_steps=[],
            parent_types=["custom_document"],  # Can have itself as parent
            allowed_personas=["user"],
        )
        db_session.add(custom_type)
        db_session.commit()

        # Create custom documents that can reference each other
        docs = []
        for i in range(4):
            doc = Document(
                user_id=test_user.id,
                document_type="custom_document",
                title=f"Custom Doc {i}",
                content_markdown=f"# Custom Doc {i}",
                domain_model={},
                doc_metadata={},
            )
            db_session.add(doc)
            docs.append(doc)
        db_session.commit()

        # Create chain: A -> B -> C -> D
        service.create_relationship(docs[0].id, docs[1].id)
        service.create_relationship(docs[1].id, docs[2].id)
        service.create_relationship(docs[2].id, docs[3].id)

        # Try to create D -> B (would create cycle: B -> C -> D -> B)
        # Note: Can't do D -> A since that would trigger duplicate check first
        with pytest.raises(ValueError, match="Circular dependency"):
            service.create_relationship(docs[3].id, docs[1].id)

    def test_no_circular_dependency_different_branches(
        self, service, test_documents, db_session, test_user
    ):
        """Test that relationships in different branches don't trigger false positive."""
        vision = test_documents["vision"]
        feature = test_documents["feature"]

        # Create two epic documents (both can have feature as parent)
        epic1 = Document(
            user_id=test_user.id,
            document_type="epic_document",
            title="Epic 1",
            content_markdown="# Epic 1",
            domain_model={},
            doc_metadata={},
        )
        epic2 = Document(
            user_id=test_user.id,
            document_type="epic_document",
            title="Epic 2",
            content_markdown="# Epic 2",
            domain_model={},
            doc_metadata={},
        )
        db_session.add_all([epic1, epic2])
        db_session.commit()

        # Create tree structure:
        #       vision
        #         |
        #      feature
        #      /     \
        #   epic1   epic2
        service.create_relationship(vision.id, feature.id)
        service.create_relationship(feature.id, epic1.id)
        service.create_relationship(feature.id, epic2.id)

        # This should succeed - epic1 and epic2 are in different branches
        # (no cycle is created)
        story = test_documents["story"]
        rel = service.create_relationship(epic1.id, story.id)
        assert rel is not None
