"""
Unit tests for hierarchy traversal methods in RelationshipService.

Tests:
- get_ancestors method with various hierarchy depths
- get_descendants method with depth limits
- get_breadcrumb method with different separators
- get_breadcrumb_with_details for structured data
- Edge cases: no relationships, multiple parents, deep hierarchies
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
    vision_type = DocumentType(
        type_name="vision_document",
        system_prompt="Vision document prompt",
        workflow_steps=[],
        parent_types=[],
        allowed_personas=["product_manager"],
    )

    feature_type = DocumentType(
        type_name="feature_document",
        system_prompt="Feature document prompt",
        workflow_steps=[],
        parent_types=["vision_document"],
        allowed_personas=["product_manager"],
    )

    epic_type = DocumentType(
        type_name="epic_document",
        system_prompt="Epic document prompt",
        workflow_steps=[],
        parent_types=["feature_document"],
        allowed_personas=["product_manager"],
    )

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
def hierarchy_documents(db_session, test_user, document_types, service):
    """Create a test hierarchy.

    Hierarchy structure:
        Vision
          |
        Feature
          |
         Epic
          |
        Story
    """
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

    # Create relationships: vision -> feature -> epic -> story
    service.create_relationship(vision.id, feature.id)
    service.create_relationship(feature.id, epic.id)
    service.create_relationship(epic.id, story.id)

    return {"vision": vision, "feature": feature, "epic": epic, "story": story}


class TestGetAncestors:
    """Test get_ancestors method."""

    def test_get_ancestors_full_hierarchy(self, service, hierarchy_documents):
        """Test getting all ancestors from bottom of hierarchy."""
        story = hierarchy_documents["story"]

        ancestors = service.get_ancestors(story.id)

        # Should get: Epic (depth 1), Feature (depth 2), Vision (depth 3)
        assert len(ancestors) == 3

        # Check order: immediate parent first
        epic_doc, epic_rel, epic_depth = ancestors[0]
        assert epic_doc.title == "Test Epic"
        assert epic_rel == "parent_child"
        assert epic_depth == 1

        feature_doc, feature_rel, feature_depth = ancestors[1]
        assert feature_doc.title == "Test Feature"
        assert feature_rel == "parent_child"
        assert feature_depth == 2

        vision_doc, vision_rel, vision_depth = ancestors[2]
        assert vision_doc.title == "Test Vision"
        assert vision_rel == "parent_child"
        assert vision_depth == 3

    def test_get_ancestors_mid_hierarchy(self, service, hierarchy_documents):
        """Test getting ancestors from middle of hierarchy."""
        epic = hierarchy_documents["epic"]

        ancestors = service.get_ancestors(epic.id)

        # Should get: Feature (depth 1), Vision (depth 2)
        assert len(ancestors) == 2
        assert ancestors[0][0].title == "Test Feature"
        assert ancestors[1][0].title == "Test Vision"

    def test_get_ancestors_no_parents(self, service, hierarchy_documents):
        """Test getting ancestors for document with no parents (root)."""
        vision = hierarchy_documents["vision"]

        ancestors = service.get_ancestors(vision.id)

        assert len(ancestors) == 0

    def test_get_ancestors_with_max_depth(self, service, hierarchy_documents):
        """Test limiting ancestor traversal depth."""
        story = hierarchy_documents["story"]

        # Limit to 2 levels
        ancestors = service.get_ancestors(story.id, max_depth=2)

        # Should only get Epic and Feature, not Vision
        assert len(ancestors) == 2
        assert ancestors[0][0].title == "Test Epic"
        assert ancestors[1][0].title == "Test Feature"

    def test_get_ancestors_nonexistent_document(self, service):
        """Test getting ancestors for non-existent document."""
        fake_id = uuid.uuid4()
        ancestors = service.get_ancestors(fake_id)
        assert len(ancestors) == 0


class TestGetDescendants:
    """Test get_descendants method."""

    def test_get_descendants_full_hierarchy(self, service, hierarchy_documents):
        """Test getting all descendants from top of hierarchy."""
        vision = hierarchy_documents["vision"]

        descendants = service.get_descendants(vision.id)

        # Should get: Feature (depth 1), Epic (depth 2), Story (depth 3)
        assert len(descendants) == 3

        # Check order: breadth-first
        feature_doc, feature_rel, feature_depth = descendants[0]
        assert feature_doc.title == "Test Feature"
        assert feature_rel == "parent_child"
        assert feature_depth == 1

        epic_doc, epic_rel, epic_depth = descendants[1]
        assert epic_doc.title == "Test Epic"
        assert epic_rel == "parent_child"
        assert epic_depth == 2

        story_doc, story_rel, story_depth = descendants[2]
        assert story_doc.title == "Test Story"
        assert story_rel == "parent_child"
        assert story_depth == 3

    def test_get_descendants_immediate_children(self, service, hierarchy_documents):
        """Test getting only immediate children (depth=1)."""
        vision = hierarchy_documents["vision"]

        descendants = service.get_descendants(vision.id, max_depth=1)

        # Should only get Feature
        assert len(descendants) == 1
        assert descendants[0][0].title == "Test Feature"
        assert descendants[0][2] == 1  # depth

    def test_get_descendants_no_children(self, service, hierarchy_documents):
        """Test getting descendants for leaf node."""
        story = hierarchy_documents["story"]

        descendants = service.get_descendants(story.id)

        assert len(descendants) == 0

    def test_get_descendants_mid_hierarchy(self, service, hierarchy_documents):
        """Test getting descendants from middle of hierarchy."""
        feature = hierarchy_documents["feature"]

        descendants = service.get_descendants(feature.id)

        # Should get: Epic (depth 1), Story (depth 2)
        assert len(descendants) == 2
        assert descendants[0][0].title == "Test Epic"
        assert descendants[1][0].title == "Test Story"

    def test_get_descendants_multiple_children(
        self, service, db_session, test_user, hierarchy_documents
    ):
        """Test getting descendants when parent has multiple children."""
        vision = hierarchy_documents["vision"]

        # Add a second feature
        feature2 = Document(
            user_id=test_user.id,
            document_type="feature_document",
            title="Test Feature 2",
            content_markdown="# Feature 2",
            domain_model={},
            doc_metadata={},
        )
        db_session.add(feature2)
        db_session.commit()

        service.create_relationship(vision.id, feature2.id)

        descendants = service.get_descendants(vision.id)

        # Should get both features (depth 1) plus original epic and story (depth 2, 3)
        assert len(descendants) == 4

        # Check that both features are at depth 1
        depth_1_docs = [doc for doc, _, depth in descendants if depth == 1]
        assert len(depth_1_docs) == 2


class TestGetBreadcrumb:
    """Test get_breadcrumb method."""

    def test_breadcrumb_full_path(self, service, hierarchy_documents):
        """Test generating breadcrumb for full hierarchy path."""
        story = hierarchy_documents["story"]

        breadcrumb = service.get_breadcrumb(story.id)

        assert breadcrumb == "Test Vision > Test Feature > Test Epic > Test Story"

    def test_breadcrumb_custom_separator(self, service, hierarchy_documents):
        """Test breadcrumb with custom separator."""
        story = hierarchy_documents["story"]

        breadcrumb = service.get_breadcrumb(story.id, separator=" / ")

        assert breadcrumb == "Test Vision / Test Feature / Test Epic / Test Story"

    def test_breadcrumb_with_ids(self, service, hierarchy_documents):
        """Test breadcrumb including document IDs."""
        story = hierarchy_documents["story"]
        vision = hierarchy_documents["vision"]

        breadcrumb = service.get_breadcrumb(story.id, include_ids=True)

        # Check that IDs are included (first 8 chars)
        assert f"Test Vision [{str(vision.id)[:8]}]" in breadcrumb
        assert "Test Feature [" in breadcrumb
        assert "Test Epic [" in breadcrumb
        assert "Test Story [" in breadcrumb

    def test_breadcrumb_root_document(self, service, hierarchy_documents):
        """Test breadcrumb for root document (no parents)."""
        vision = hierarchy_documents["vision"]

        breadcrumb = service.get_breadcrumb(vision.id)

        assert breadcrumb == "Test Vision"

    def test_breadcrumb_mid_hierarchy(self, service, hierarchy_documents):
        """Test breadcrumb from middle of hierarchy."""
        epic = hierarchy_documents["epic"]

        breadcrumb = service.get_breadcrumb(epic.id)

        assert breadcrumb == "Test Vision > Test Feature > Test Epic"

    def test_breadcrumb_nonexistent_document(self, service):
        """Test breadcrumb for non-existent document."""
        fake_id = uuid.uuid4()
        breadcrumb = service.get_breadcrumb(fake_id)
        assert breadcrumb == ""


class TestGetBreadcrumbWithDetails:
    """Test get_breadcrumb_with_details method."""

    def test_breadcrumb_details_full_path(self, service, hierarchy_documents):
        """Test getting breadcrumb with full details."""
        story = hierarchy_documents["story"]

        details = service.get_breadcrumb_with_details(story.id)

        # Should have 4 items: vision, feature, epic, story
        assert len(details) == 4

        # Check structure
        assert details[0]["title"] == "Test Vision"
        assert details[0]["document_type"] == "vision_document"
        assert details[0]["relationship_type"] == "parent_child"
        assert "id" in details[0]

        assert details[1]["title"] == "Test Feature"
        assert details[1]["document_type"] == "feature_document"
        assert details[1]["relationship_type"] == "parent_child"

        assert details[2]["title"] == "Test Epic"
        assert details[2]["document_type"] == "epic_document"
        assert details[2]["relationship_type"] == "parent_child"

        # Current document has no relationship_type
        assert details[3]["title"] == "Test Story"
        assert details[3]["document_type"] == "user_story"
        assert details[3]["relationship_type"] is None

    def test_breadcrumb_details_root_document(self, service, hierarchy_documents):
        """Test breadcrumb details for root document."""
        vision = hierarchy_documents["vision"]

        details = service.get_breadcrumb_with_details(vision.id)

        # Should only have vision itself
        assert len(details) == 1
        assert details[0]["title"] == "Test Vision"
        assert details[0]["relationship_type"] is None

    def test_breadcrumb_details_nonexistent_document(self, service):
        """Test breadcrumb details for non-existent document."""
        fake_id = uuid.uuid4()
        details = service.get_breadcrumb_with_details(fake_id)
        assert details == []


class TestComplexHierarchies:
    """Test traversal with complex hierarchy scenarios."""

    def test_wide_hierarchy(self, service, db_session, test_user, hierarchy_documents):
        """Test hierarchy with multiple children at same level."""
        vision = hierarchy_documents["vision"]

        # Create 3 features under vision
        features = []
        for i in range(3):
            feature = Document(
                user_id=test_user.id,
                document_type="feature_document",
                title=f"Feature {i}",
                content_markdown=f"# Feature {i}",
                domain_model={},
                doc_metadata={},
            )
            db_session.add(feature)
            features.append(feature)

        db_session.commit()

        # Create relationships
        for feature in features:
            service.create_relationship(vision.id, feature.id)

        # Get all descendants
        descendants = service.get_descendants(vision.id)

        # Should have original feature + 3 new features + epic + story
        # = 6 total
        assert len(descendants) >= 5  # At least the 3 new features + epic + story

        # All new features should be at depth 1
        depth_1_count = sum(1 for _, _, depth in descendants if depth == 1)
        assert depth_1_count >= 3

    def test_deep_hierarchy(self, service, db_session, test_user, document_types):
        """Test very deep hierarchy (6 levels)."""
        # Create custom type that allows itself as parent
        custom_type = DocumentType(
            type_name="custom_doc",
            system_prompt="Custom",
            workflow_steps=[],
            parent_types=["custom_doc"],
            allowed_personas=["user"],
        )
        db_session.add(custom_type)
        db_session.commit()

        # Create 6-level hierarchy
        docs = []
        for i in range(6):
            doc = Document(
                user_id=test_user.id,
                document_type="custom_doc",
                title=f"Level {i}",
                content_markdown=f"# Level {i}",
                domain_model={},
                doc_metadata={},
            )
            db_session.add(doc)
            docs.append(doc)

        db_session.commit()

        # Create chain: 0 -> 1 -> 2 -> 3 -> 4 -> 5
        for i in range(5):
            service.create_relationship(docs[i].id, docs[i + 1].id)

        # Get ancestors from bottom
        ancestors = service.get_ancestors(docs[5].id)
        assert len(ancestors) == 5

        # Get descendants from top
        descendants = service.get_descendants(docs[0].id)
        assert len(descendants) == 5

        # Check breadcrumb
        breadcrumb = service.get_breadcrumb(docs[5].id)
        assert breadcrumb == "Level 0 > Level 1 > Level 2 > Level 3 > Level 4 > Level 5"
