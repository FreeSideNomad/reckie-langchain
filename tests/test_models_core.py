"""
Tests for core database models (User, DocumentType, Document).

Tests:
- Model creation and validation
- Relationships between models
- JSONB field operations
- Validators and constraints
- Helper methods
"""

import pytest
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.database.base import Base
from src.database.models.user import User
from src.database.models.document_type import DocumentType
from src.database.models.document import Document


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


class TestUserModel:
    """Test User model functionality."""

    def test_create_user(self, session):
        """Test creating a user with valid data."""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            role="user"
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"

    def test_email_lowercase_validation(self, session):
        """Test email is automatically converted to lowercase."""
        user = User(
            username="testuser",
            email="TEST@EXAMPLE.COM",
            password_hash="hash",
            role="user"
        )
        session.add(user)
        session.commit()

        assert user.email == "test@example.com"

    def test_invalid_email_format(self):
        """Test invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            User(
                username="testuser",
                email="invalid-email",
                password_hash="hash",
                role="user"
            )

    def test_invalid_role(self):
        """Test invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            User(
                username="testuser",
                email="test@example.com",
                password_hash="hash",
                role="invalid_role"
            )

    def test_valid_roles(self, session):
        """Test all valid roles are accepted."""
        valid_roles = ["user", "admin", "qa_lead", "ddd_designer"]

        for role in valid_roles:
            user = User(
                username=f"user_{role}",
                email=f"{role}@example.com",
                password_hash="hash",
                role=role
            )
            session.add(user)
            session.commit()

            assert user.role == role
            session.expunge(user)

    def test_unique_username(self, session):
        """Test username must be unique."""
        user1 = User(
            username="duplicate",
            email="user1@example.com",
            password_hash="hash",
            role="user"
        )
        session.add(user1)
        session.commit()

        user2 = User(
            username="duplicate",
            email="user2@example.com",
            password_hash="hash",
            role="user"
        )
        session.add(user2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_repr(self):
        """Test User __repr__ method."""
        user = User(
            id=uuid.uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            role="admin"
        )
        repr_str = repr(user)

        assert "User" in repr_str
        assert "testuser" in repr_str
        assert "admin" in repr_str


class TestDocumentTypeModel:
    """Test DocumentType model functionality."""

    def test_create_document_type(self, session):
        """Test creating a document type."""
        doc_type = DocumentType(
            type_name="vision_document",
            system_prompt="You are a product owner...",
            workflow_steps=[
                {"step_id": "define_vision", "question_count": 5}
            ],
            parent_types=["research_report", "business_context"],
            allowed_personas=["product_owner"]
        )
        session.add(doc_type)
        session.commit()

        assert doc_type.id is not None
        assert doc_type.type_name == "vision_document"
        assert len(doc_type.workflow_steps) == 1
        assert len(doc_type.parent_types) == 2
        assert "product_owner" in doc_type.allowed_personas

    def test_type_name_validation(self):
        """Test type_name is converted to lowercase with underscores."""
        doc_type = DocumentType(
            type_name="Vision Document",
            system_prompt="Test",
            workflow_steps=[]
        )

        validated_name = doc_type.validate_type_name("type_name", "Vision Document")
        assert validated_name == "vision_document"

    def test_workflow_step_count(self, session):
        """Test workflow_step_count hybrid property."""
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[
                {"step_id": "step1"},
                {"step_id": "step2"},
                {"step_id": "step3"}
            ]
        )
        session.add(doc_type)
        session.commit()

        assert doc_type.workflow_step_count == 3

    def test_get_workflow_step(self, session):
        """Test getting a specific workflow step."""
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[
                {"step_id": "step1", "name": "First Step"},
                {"step_id": "step2", "name": "Second Step"}
            ]
        )
        session.add(doc_type)
        session.commit()

        step = doc_type.get_workflow_step("step1")
        assert step["name"] == "First Step"

    def test_get_workflow_step_not_found(self, session):
        """Test getting non-existent workflow step raises error."""
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[{"step_id": "step1"}]
        )
        session.add(doc_type)
        session.commit()

        with pytest.raises(ValueError, match="not found"):
            doc_type.get_workflow_step("nonexistent")

    def test_is_parent_allowed(self, session):
        """Test checking if parent type is allowed."""
        doc_type = DocumentType(
            type_name="feature_document",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=["vision_document"]
        )
        session.add(doc_type)
        session.commit()

        assert doc_type.is_parent_allowed("vision_document") is True
        assert doc_type.is_parent_allowed("epic_document") is False

    def test_is_persona_allowed(self, session):
        """Test checking if persona is allowed."""
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[],
            allowed_personas=["product_owner", "business_analyst"]
        )
        session.add(doc_type)
        session.commit()

        assert doc_type.is_persona_allowed("product_owner") is True
        assert doc_type.is_persona_allowed("qa_lead") is False


class TestDocumentModel:
    """Test Document model functionality."""

    def test_create_document(self, session):
        """Test creating a document."""
        # Create user first
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            role="user"
        )
        session.add(user)
        session.commit()

        # Create document type
        doc_type = DocumentType(
            type_name="vision_document",
            system_prompt="Test",
            workflow_steps=[]
        )
        session.add(doc_type)
        session.commit()

        # Create document
        document = Document(
            user_id=user.id,
            document_type=doc_type.type_name,
            title="Test Vision",
            content_markdown="# Vision Content",
            status="draft"
        )
        session.add(document)
        session.commit()

        assert document.id is not None
        assert document.title == "Test Vision"
        assert document.status == "draft"
        assert document.version == 1

    def test_status_validation(self):
        """Test status validation."""
        with pytest.raises(ValueError, match="Invalid status"):
            Document(
                user_id=uuid.uuid4(),
                document_type="test_type",
                title="Test",
                status="invalid_status"
            )

    def test_valid_statuses(self, session):
        """Test all valid statuses are accepted."""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            role="user"
        )
        session.add(user)
        session.commit()

        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[]
        )
        session.add(doc_type)
        session.commit()

        valid_statuses = ["draft", "in_progress", "complete", "stale"]

        for status in valid_statuses:
            document = Document(
                user_id=user.id,
                document_type=doc_type.type_name,
                title=f"Doc {status}",
                status=status
            )
            session.add(document)
            session.commit()

            assert document.status == status
            session.expunge(document)

    def test_version_validation(self):
        """Test version must be positive."""
        with pytest.raises(ValueError, match="Version must be >= 1"):
            Document(
                user_id=uuid.uuid4(),
                document_type="test_type",
                title="Test",
                version=0
            )

    def test_metadata_operations(self, session):
        """Test metadata get/set operations."""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            role="user"
        )
        session.add(user)

        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[]
        )
        session.add(doc_type)
        session.commit()

        document = Document(
            user_id=user.id,
            document_type=doc_type.type_name,
            title="Test",
            doc_metadata={"priority": "P0", "tags": ["important"]}
        )
        session.add(document)
        session.commit()

        # Test get_metadata_value
        assert document.get_metadata_value("priority") == "P0"
        assert document.get_metadata_value("nonexistent", "default") == "default"

        # Test set_metadata_value
        document.set_metadata_value("story_points", 5)
        assert document.get_metadata_value("story_points") == 5

    def test_helper_methods(self, session):
        """Test helper methods (is_complete, mark_complete, etc.)."""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            role="user"
        )
        session.add(user)

        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[]
        )
        session.add(doc_type)
        session.commit()

        document = Document(
            user_id=user.id,
            document_type=doc_type.type_name,
            title="Test",
            status="draft",
            version=1
        )
        session.add(document)
        session.commit()

        # Test is_draft
        assert document.is_draft() is True
        assert document.is_complete() is False

        # Test mark_complete
        document.mark_complete()
        assert document.status == "complete"
        assert document.is_complete() is True

        # Test mark_stale
        document.mark_stale()
        assert document.status == "stale"

        # Test increment_version
        document.increment_version()
        assert document.version == 2


def test_user_document_relationship(session):
    """Test relationship between User and Document."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hash",
        role="user"
    )
    session.add(user)

    doc_type = DocumentType(
        type_name="test_type",
        system_prompt="Test",
        workflow_steps=[]
    )
    session.add(doc_type)
    session.commit()

    doc1 = Document(
        user_id=user.id,
        document_type=doc_type.type_name,
        title="Doc 1"
    )
    doc2 = Document(
        user_id=user.id,
        document_type=doc_type.type_name,
        title="Doc 2"
    )
    session.add_all([doc1, doc2])
    session.commit()

    # Test relationship
    assert len(user.documents) == 2
    assert doc1.user.username == "testuser"
    assert doc2.user.username == "testuser"


def test_document_type_invalid_workflow_steps():
    """Test workflow_steps must be a list."""
    with pytest.raises(ValueError, match="workflow_steps must be a list"):
        DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps="not_a_list"  # Invalid: should be list
        )


def test_document_type_name_with_invalid_chars():
    """Test type_name validation with invalid characters."""
    with pytest.raises(ValueError, match="Must contain only"):
        DocumentType(
            type_name="test-type!",  # Invalid: contains special chars
            system_prompt="Test",
            workflow_steps=[]
        )


def test_document_get_domain_model_value(session):
    """Test get_domain_model_value helper."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hash",
        role="user"
    )
    session.add(user)

    doc_type = DocumentType(
        type_name="test_type",
        system_prompt="Test",
        workflow_steps=[]
    )
    session.add(doc_type)
    session.commit()

    document = Document(
        user_id=user.id,
        document_type=doc_type.type_name,
        title="Test",
        domain_model={"key1": "value1", "key2": 123}
    )
    session.add(document)
    session.commit()

    # Test get_domain_model_value
    assert document.get_domain_model_value("key1") == "value1"
    assert document.get_domain_model_value("key2") == 123
    assert document.get_domain_model_value("missing", "default") == "default"


def test_document_is_draft(session):
    """Test is_draft helper."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hash",
        role="user"
    )
    session.add(user)

    doc_type = DocumentType(
        type_name="test_type",
        system_prompt="Test",
        workflow_steps=[]
    )
    session.add(doc_type)
    session.commit()

    document = Document(
        user_id=user.id,
        document_type=doc_type.type_name,
        title="Test",
        status="draft"
    )
    session.add(document)
    session.commit()

    assert document.is_draft() is True

    document.status = "in_progress"
    assert document.is_draft() is False
