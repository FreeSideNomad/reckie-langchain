"""
Tests for relationship models (DocumentRelationship, Conversation, DocumentVersion).

Tests:
- Model creation and validation
- Relationships between models
- JSONB field operations
- Validators and constraints
- Helper methods
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.base import Base
from src.database.models.conversation import Conversation
from src.database.models.document import Document
from src.database.models.document_relationship import DocumentRelationship
from src.database.models.document_type import DocumentType
from src.database.models.document_version import DocumentVersion
from src.database.models.user import User


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def user(session):
    """Create a test user."""
    user = User(username="testuser", email="test@example.com", password_hash="hash", role="user")
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def doc_type(session):
    """Create a test document type."""
    doc_type = DocumentType(type_name="test_type", system_prompt="Test", workflow_steps=[])
    session.add(doc_type)
    session.commit()
    return doc_type


@pytest.fixture
def document(session, user, doc_type):
    """Create a test document."""
    document = Document(user_id=user.id, document_type=doc_type.type_name, title="Test Document")
    session.add(document)
    session.commit()
    return document


class TestDocumentRelationshipModel:
    """Test DocumentRelationship model functionality."""

    def test_create_relationship(self, session, user, doc_type):
        """Test creating a document relationship."""
        parent = Document(user_id=user.id, document_type=doc_type.type_name, title="Parent Doc")
        child = Document(user_id=user.id, document_type=doc_type.type_name, title="Child Doc")
        session.add_all([parent, child])
        session.commit()

        relationship = DocumentRelationship(
            parent_id=parent.id, child_id=child.id, relationship_type="parent_child"
        )
        session.add(relationship)
        session.commit()

        assert relationship.id is not None
        assert relationship.parent_id == parent.id
        assert relationship.child_id == child.id
        assert relationship.relationship_type == "parent_child"

    def test_relationship_type_validation(self):
        """Test relationship_type validation."""
        with pytest.raises(ValueError, match="Invalid relationship_type"):
            DocumentRelationship(
                parent_id=uuid.uuid4(), child_id=uuid.uuid4(), relationship_type="invalid_type"
            )

    def test_valid_relationship_types(self, session, user, doc_type):
        """Test all valid relationship types are accepted."""
        parent = Document(user_id=user.id, document_type=doc_type.type_name, title="Parent")
        session.add(parent)
        session.commit()

        valid_types = ["parent_child", "reference", "derived_from"]

        for rel_type in valid_types:
            child = Document(
                user_id=user.id, document_type=doc_type.type_name, title=f"Child {rel_type}"
            )
            session.add(child)
            session.commit()

            rel = DocumentRelationship(
                parent_id=parent.id, child_id=child.id, relationship_type=rel_type
            )
            session.add(rel)
            session.commit()

            assert rel.relationship_type == rel_type
            session.expunge(rel)

    def test_unique_constraint(self, session, user, doc_type):
        """Test unique constraint on (parent_id, child_id)."""
        parent = Document(user_id=user.id, document_type=doc_type.type_name, title="Parent")
        child = Document(user_id=user.id, document_type=doc_type.type_name, title="Child")
        session.add_all([parent, child])
        session.commit()

        rel1 = DocumentRelationship(
            parent_id=parent.id, child_id=child.id, relationship_type="parent_child"
        )
        session.add(rel1)
        session.commit()

        rel2 = DocumentRelationship(
            parent_id=parent.id, child_id=child.id, relationship_type="reference"
        )
        session.add(rel2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_relationship_back_populates(self, session, user, doc_type):
        """Test relationship back-populates work correctly."""
        parent = Document(user_id=user.id, document_type=doc_type.type_name, title="Parent")
        child = Document(user_id=user.id, document_type=doc_type.type_name, title="Child")
        session.add_all([parent, child])
        session.commit()

        rel = DocumentRelationship(
            parent_id=parent.id, child_id=child.id, relationship_type="parent_child"
        )
        session.add(rel)
        session.commit()

        # Test back-populates
        assert len(parent.child_relationships) == 1
        assert len(child.parent_relationships) == 1
        assert parent.child_relationships[0].child_id == child.id
        assert child.parent_relationships[0].parent_id == parent.id


class TestConversationModel:
    """Test Conversation model functionality."""

    def test_create_conversation(self, session, user, document):
        """Test creating a conversation."""
        conversation = Conversation(user_id=user.id, document_id=document.id, history=[], state={})
        session.add(conversation)
        session.commit()

        assert conversation.id is not None
        assert conversation.user_id == user.id
        assert conversation.document_id == document.id
        assert conversation.history == []
        assert conversation.state == {}

    def test_add_message(self, session, user, document):
        """Test add_message helper."""
        conversation = Conversation(user_id=user.id, document_id=document.id)
        session.add(conversation)
        session.commit()

        conversation.add_message("user", "Hello")
        conversation.add_message("assistant", "Hi there!")

        assert len(conversation.history) == 2
        assert conversation.history[0]["role"] == "user"
        assert conversation.history[0]["content"] == "Hello"
        assert conversation.history[1]["role"] == "assistant"
        assert "timestamp" in conversation.history[0]

    def test_get_current_step(self, session, user, document):
        """Test get_current_step helper."""
        conversation = Conversation(
            user_id=user.id,
            document_id=document.id,
            state={"current_step": "step1", "turn_count": 3},
        )
        session.add(conversation)
        session.commit()

        assert conversation.get_current_step() == "step1"

    def test_update_workflow_state(self, session, user, document):
        """Test update_workflow_state helper."""
        conversation = Conversation(user_id=user.id, document_id=document.id)
        session.add(conversation)
        session.commit()

        conversation.update_workflow_state("current_step", "step2")
        conversation.update_workflow_state("turn_count", 5)

        assert conversation.state["current_step"] == "step2"
        assert conversation.state["turn_count"] == 5

    def test_get_message_count(self, session, user, document):
        """Test get_message_count helper."""
        conversation = Conversation(user_id=user.id, document_id=document.id)
        session.add(conversation)
        session.commit()

        assert conversation.get_message_count() == 0

        conversation.add_message("user", "Test")
        assert conversation.get_message_count() == 1

    def test_unique_user_document_constraint(self, session, user, document):
        """Test unique constraint on (user_id, document_id)."""
        conv1 = Conversation(user_id=user.id, document_id=document.id)
        session.add(conv1)
        session.commit()

        conv2 = Conversation(user_id=user.id, document_id=document.id)
        session.add(conv2)

        with pytest.raises(IntegrityError):
            session.commit()


class TestDocumentVersionModel:
    """Test DocumentVersion model functionality."""

    def test_create_version(self, session, user, document):
        """Test creating a document version."""
        version = DocumentVersion(
            document_id=document.id,
            version=1,
            content_markdown="# Version 1",
            domain_model={"key": "value"},
            changed_by=user.id,
            change_description="Initial version",
        )
        session.add(version)
        session.commit()

        assert version.id is not None
        assert version.document_id == document.id
        assert version.version == 1
        assert version.content_markdown == "# Version 1"
        assert version.domain_model == {"key": "value"}
        assert version.changed_by == user.id

    def test_version_validation(self):
        """Test version must be positive."""
        with pytest.raises(ValueError, match="Version must be >= 1"):
            DocumentVersion(document_id=uuid.uuid4(), version=0, content_markdown="Test")

    def test_unique_document_version_constraint(self, session, document, user):
        """Test unique constraint on (document_id, version)."""
        v1 = DocumentVersion(
            document_id=document.id, version=1, content_markdown="V1", changed_by=user.id
        )
        session.add(v1)
        session.commit()

        v2 = DocumentVersion(
            document_id=document.id, version=1, content_markdown="V1 duplicate", changed_by=user.id
        )
        session.add(v2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_get_domain_model_value(self, session, document, user):
        """Test get_domain_model_value helper."""
        version = DocumentVersion(
            document_id=document.id,
            version=1,
            domain_model={"key1": "value1", "key2": 123},
            changed_by=user.id,
        )
        session.add(version)
        session.commit()

        assert version.get_domain_model_value("key1") == "value1"
        assert version.get_domain_model_value("key2") == 123
        assert version.get_domain_model_value("missing", "default") == "default"

    def test_version_relationship(self, session, user, document):
        """Test relationship between Document and DocumentVersion."""
        v1 = DocumentVersion(
            document_id=document.id, version=1, content_markdown="V1", changed_by=user.id
        )
        v2 = DocumentVersion(
            document_id=document.id, version=2, content_markdown="V2", changed_by=user.id
        )
        session.add_all([v1, v2])
        session.commit()

        # Test relationship
        assert len(document.versions) == 2
        assert v1.document.title == document.title
        assert v2.document.title == document.title


def test_conversation_relationship(session, user, document):
    """Test relationship between User/Document and Conversation."""
    conv = Conversation(user_id=user.id, document_id=document.id)
    session.add(conv)
    session.commit()

    # Test relationships
    assert len(user.conversations) == 1
    assert len(document.conversations) == 1
    assert conv.user.username == user.username
    assert conv.document.title == document.title
