"""
Unit tests for ripple effect and parent context methods in RelationshipService.

Tests:
- mark_descendants_for_review method with various scenarios
- get_parent_context method with different hierarchy depths
- Edge cases: no descendants, no ancestors, large content
"""

import uuid
from datetime import datetime, timezone

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
        content_markdown="# Vision\nThis is our product vision for 2024.",
        domain_model={},
        doc_metadata={},
    )

    feature = Document(
        user_id=test_user.id,
        document_type="feature_document",
        title="Test Feature",
        content_markdown="# Feature\nThis feature implements user authentication.",
        domain_model={},
        doc_metadata={},
    )

    epic = Document(
        user_id=test_user.id,
        document_type="epic_document",
        title="Test Epic",
        content_markdown="# Epic\nSocial login integration.",
        domain_model={},
        doc_metadata={},
    )

    story = Document(
        user_id=test_user.id,
        document_type="user_story",
        title="Test Story",
        content_markdown="# Story\nAs a user, I want to login with Google.",
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


class TestMarkDescendantsForReview:
    """Test mark_descendants_for_review method."""

    def test_mark_all_descendants(self, service, hierarchy_documents, db_session):
        """Test marking all descendants when root changes."""
        vision = hierarchy_documents["vision"]
        feature = hierarchy_documents["feature"]
        epic = hierarchy_documents["epic"]
        story = hierarchy_documents["story"]

        # Mark descendants
        count = service.mark_descendants_for_review(vision.id)

        # Should mark 3 descendants: feature, epic, story
        assert count == 3

        # Refresh from database
        db_session.refresh(feature)
        db_session.refresh(epic)
        db_session.refresh(story)

        # Check feature metadata
        assert feature.doc_metadata["needs_review"] is True
        assert "parent_changed" in feature.doc_metadata
        assert feature.doc_metadata["parent_changed"]["parent_id"] == str(vision.id)
        assert feature.doc_metadata["parent_changed"]["depth_from_changed"] == 1
        assert "changed_at" in feature.doc_metadata["parent_changed"]

        # Check epic metadata
        assert epic.doc_metadata["needs_review"] is True
        assert epic.doc_metadata["parent_changed"]["depth_from_changed"] == 2

        # Check story metadata
        assert story.doc_metadata["needs_review"] is True
        assert story.doc_metadata["parent_changed"]["depth_from_changed"] == 3

    def test_mark_descendants_with_depth_limit(self, service, hierarchy_documents, db_session):
        """Test marking descendants with depth limit."""
        vision = hierarchy_documents["vision"]
        feature = hierarchy_documents["feature"]
        epic = hierarchy_documents["epic"]
        story = hierarchy_documents["story"]

        # Mark only 2 levels deep
        count = service.mark_descendants_for_review(vision.id, max_depth=2)

        # Should mark only feature and epic
        assert count == 2

        # Refresh from database
        db_session.refresh(feature)
        db_session.refresh(epic)
        db_session.refresh(story)

        # Feature and epic should be marked
        assert feature.doc_metadata["needs_review"] is True
        assert epic.doc_metadata["needs_review"] is True

        # Story should NOT be marked
        assert story.doc_metadata.get("needs_review") is None

    def test_mark_descendants_no_children(self, service, hierarchy_documents):
        """Test marking descendants when node has no children."""
        story = hierarchy_documents["story"]

        # Mark descendants (leaf node)
        count = service.mark_descendants_for_review(story.id)

        # Should mark 0 descendants
        assert count == 0

    def test_mark_descendants_mid_hierarchy(self, service, hierarchy_documents, db_session):
        """Test marking descendants from middle of hierarchy."""
        feature = hierarchy_documents["feature"]
        epic = hierarchy_documents["epic"]
        story = hierarchy_documents["story"]

        # Mark descendants from feature
        count = service.mark_descendants_for_review(feature.id)

        # Should mark epic and story
        assert count == 2

        # Refresh from database
        db_session.refresh(epic)
        db_session.refresh(story)

        # Check epic metadata
        assert epic.doc_metadata["needs_review"] is True
        assert epic.doc_metadata["parent_changed"]["parent_id"] == str(feature.id)
        assert epic.doc_metadata["parent_changed"]["depth_from_changed"] == 1

        # Check story metadata
        assert story.doc_metadata["needs_review"] is True
        assert story.doc_metadata["parent_changed"]["depth_from_changed"] == 2

    def test_mark_descendants_preserves_existing_metadata(
        self, service, hierarchy_documents, db_session
    ):
        """Test that marking preserves existing metadata."""
        feature = hierarchy_documents["feature"]

        # Add existing metadata
        feature.doc_metadata = {"custom_field": "value", "other": 123}
        db_session.commit()

        # Mark descendants
        service.mark_descendants_for_review(hierarchy_documents["vision"].id)

        # Refresh from database
        db_session.refresh(feature)

        # Should have both old and new metadata
        assert feature.doc_metadata["custom_field"] == "value"
        assert feature.doc_metadata["other"] == 123
        assert feature.doc_metadata["needs_review"] is True
        assert "parent_changed" in feature.doc_metadata


class TestGetParentContext:
    """Test get_parent_context method."""

    def test_get_full_parent_context(self, service, hierarchy_documents):
        """Test getting parent context for full hierarchy."""
        story = hierarchy_documents["story"]

        context = service.get_parent_context(story.id)

        # Should include all 3 parents
        assert "# Parent Context" in context
        assert "## vision_document: Test Vision" in context
        assert "## feature_document: Test Feature" in context
        assert "## epic_document: Test Epic" in context

        # Should include content
        assert "This is our product vision for 2024" in context
        assert "This feature implements user authentication" in context
        assert "Social login integration" in context

        # Should be in order from root to immediate parent
        vision_pos = context.find("Test Vision")
        feature_pos = context.find("Test Feature")
        epic_pos = context.find("Test Epic")
        assert vision_pos < feature_pos < epic_pos

    def test_get_parent_context_no_parents(self, service, hierarchy_documents):
        """Test getting parent context for root document."""
        vision = hierarchy_documents["vision"]

        context = service.get_parent_context(vision.id)

        # Should return empty string
        assert context == ""

    def test_get_parent_context_mid_hierarchy(self, service, hierarchy_documents):
        """Test getting parent context from middle of hierarchy."""
        epic = hierarchy_documents["epic"]

        context = service.get_parent_context(epic.id)

        # Should include vision and feature
        assert "## vision_document: Test Vision" in context
        assert "## feature_document: Test Feature" in context

        # Should NOT include epic itself
        assert "## epic_document: Test Epic" not in context

    def test_get_parent_context_truncates_long_content(
        self, service, hierarchy_documents, db_session
    ):
        """Test that long parent content is truncated."""
        vision = hierarchy_documents["vision"]

        # Set very long content
        long_content = "A" * 5000
        vision.content_markdown = long_content
        db_session.commit()

        # Get context with small limit
        context = service.get_parent_context(
            hierarchy_documents["story"].id, max_chars_per_parent=100
        )

        # Should be truncated
        assert "[...truncated]" in context
        # Count 'A' characters - should be roughly 100
        a_count = context.count("A")
        assert 90 <= a_count <= 110  # Allow some margin for formatting

    def test_get_parent_context_handles_none_content(
        self, service, hierarchy_documents, db_session
    ):
        """Test handling of None content_markdown."""
        vision = hierarchy_documents["vision"]

        # Set content to None
        vision.content_markdown = None
        db_session.commit()

        context = service.get_parent_context(hierarchy_documents["story"].id)

        # Should still work, just with empty content
        assert "## vision_document: Test Vision" in context
        # Should have other parents
        assert "## feature_document: Test Feature" in context

    def test_get_parent_context_formatting(self, service, hierarchy_documents):
        """Test that context is properly formatted with spacing."""
        story = hierarchy_documents["story"]

        context = service.get_parent_context(story.id)

        # Should have proper markdown structure
        assert context.startswith("# Parent Context\n")

        # Should have spacing between sections
        lines = context.split("\n")
        # Count empty lines (spacing)
        empty_lines = sum(1 for line in lines if line.strip() == "")
        # Should have at least a few empty lines for spacing
        assert empty_lines >= 3


class TestEdgeCases:
    """Test edge cases for ripple effect and context."""

    def test_mark_descendants_nonexistent_document(self, service):
        """Test marking descendants for non-existent document."""
        fake_id = uuid.uuid4()

        # Should return 0 (no descendants)
        count = service.mark_descendants_for_review(fake_id)
        assert count == 0

    def test_get_parent_context_nonexistent_document(self, service):
        """Test getting context for non-existent document."""
        fake_id = uuid.uuid4()

        # Should return empty string
        context = service.get_parent_context(fake_id)
        assert context == ""

    def test_mark_descendants_multiple_times(self, service, hierarchy_documents, db_session):
        """Test marking descendants multiple times (updates metadata)."""
        vision = hierarchy_documents["vision"]
        feature = hierarchy_documents["feature"]

        # Mark first time
        service.mark_descendants_for_review(vision.id)
        db_session.refresh(feature)
        first_changed_at = feature.doc_metadata["parent_changed"]["changed_at"]

        # Mark second time
        service.mark_descendants_for_review(vision.id)
        db_session.refresh(feature)
        second_changed_at = feature.doc_metadata["parent_changed"]["changed_at"]

        # Timestamp should be updated
        assert second_changed_at >= first_changed_at
