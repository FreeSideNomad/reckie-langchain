"""Integration tests for Document CRUD API endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.dependencies import get_db
from src.api.main import app
from src.database.base import Base
from src.database.models.document import Document  # noqa: F401 - Needed for table creation
from src.database.models.document_type import DocumentType
from src.database.models.user import User


@pytest.fixture(scope="function")
def test_engine():
    """Create test database engine for each test."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Use single connection pool for in-memory DB
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(test_engine):
    """Create FastAPI test client with test database."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_engine):
    """Create a test user."""
    SessionLocal = sessionmaker(bind=test_engine)
    db = SessionLocal()
    try:
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def test_document_type(test_engine):
    """Create a test document type."""
    SessionLocal = sessionmaker(bind=test_engine)
    db = SessionLocal()
    try:
        doc_type = DocumentType(
            type_name="test_doc",
            system_prompt="Test document type system prompt",
            workflow_steps=[],
            parent_types=[],
            allowed_personas=["user"],
            config={},
        )
        db.add(doc_type)
        db.commit()
        db.refresh(doc_type)
        return doc_type
    finally:
        db.close()


@pytest.fixture
def test_db(test_engine):
    """Create test database session (for direct database operations in tests)."""
    SessionLocal = sessionmaker(bind=test_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestCreateDocument:
    """Test POST /api/v1/documents/."""

    def test_create_document_success(self, client, test_user, test_document_type):
        """Test successful document creation."""
        document_data = {
            "user_id": str(test_user.id),
            "document_type": test_document_type.type_name,
            "title": "Test Document",
            "content_markdown": "# Test Content",
            "domain_model": {"key": "value"},
            "doc_metadata": {"tags": ["test"]},
            "status": "draft",
        }

        response = client.post("/api/v1/documents/", json=document_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Document"
        assert data["document_type"] == test_document_type.type_name
        assert data["user_id"] == str(test_user.id)
        assert data["status"] == "draft"
        assert data["version"] == 1
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_document_minimal_fields(self, client, test_user, test_document_type):
        """Test document creation with only required fields."""
        document_data = {
            "user_id": str(test_user.id),
            "document_type": test_document_type.type_name,
            "title": "Minimal Document",
        }

        response = client.post("/api/v1/documents/", json=document_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Document"
        assert data["content_markdown"] is None
        assert data["domain_model"] == {}
        assert data["doc_metadata"] == {}
        assert data["status"] == "draft"

    def test_create_document_invalid_status(self, client, test_user, test_document_type):
        """Test document creation with invalid status."""
        document_data = {
            "user_id": str(test_user.id),
            "document_type": test_document_type.type_name,
            "title": "Test Document",
            "status": "invalid_status",
        }

        response = client.post("/api/v1/documents/", json=document_data)

        assert response.status_code == 422

    def test_create_document_missing_required_fields(self, client):
        """Test document creation with missing required fields."""
        document_data = {"title": "Test Document"}

        response = client.post("/api/v1/documents/", json=document_data)

        assert response.status_code == 422


class TestListDocuments:
    """Test GET /api/v1/documents/."""

    def test_list_documents_empty(self, client):
        """Test listing documents when none exist."""
        response = client.get("/api/v1/documents/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 0

    def test_list_documents_with_data(self, client, test_user, test_document_type):
        """Test listing documents with existing data."""
        # Create test documents
        for i in range(3):
            doc_data = {
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": f"Document {i + 1}",
            }
            client.post("/api/v1/documents/", json=doc_data)

        response = client.get("/api/v1/documents/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["total_pages"] == 1

    def test_list_documents_pagination(self, client, test_user, test_document_type):
        """Test pagination of document list."""
        # Create 15 test documents
        for i in range(15):
            doc_data = {
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": f"Document {i + 1}",
            }
            client.post("/api/v1/documents/", json=doc_data)

        # Get first page
        response = client.get("/api/v1/documents/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["page"] == 1
        assert data["total_pages"] == 3

        # Get second page
        response = client.get("/api/v1/documents/?page=2&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2

    def test_list_documents_filter_by_type(self, client, test_user, test_db):
        """Test filtering documents by type."""
        # Create two document types
        type1 = DocumentType(
            type_name="type1",
            system_prompt="Type 1 prompt",
            workflow_steps=[],
        )
        type2 = DocumentType(
            type_name="type2",
            system_prompt="Type 2 prompt",
            workflow_steps=[],
        )
        test_db.add(type1)
        test_db.add(type2)
        test_db.commit()

        # Create documents of different types
        client.post(
            "/api/v1/documents/",
            json={"user_id": str(test_user.id), "document_type": "type1", "title": "Doc 1"},
        )
        client.post(
            "/api/v1/documents/",
            json={"user_id": str(test_user.id), "document_type": "type2", "title": "Doc 2"},
        )

        # Filter by type1
        response = client.get("/api/v1/documents/?document_type=type1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["document_type"] == "type1"

    def test_list_documents_filter_by_status(self, client, test_user, test_document_type):
        """Test filtering documents by status."""
        # Create documents with different statuses
        client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Draft Doc",
                "status": "draft",
            },
        )
        client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Complete Doc",
                "status": "complete",
            },
        )

        # Filter by status
        response = client.get("/api/v1/documents/?status=draft")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "draft"

    def test_list_documents_filter_by_user(self, client, test_db, test_document_type):
        """Test filtering documents by user ID."""
        # Create two users
        user1 = User(
            id=uuid.uuid4(),
            email="user1@example.com",
            username="user1",
            password_hash="hash1",
        )
        user2 = User(
            id=uuid.uuid4(),
            email="user2@example.com",
            username="user2",
            password_hash="hash2",
        )
        test_db.add(user1)
        test_db.add(user2)
        test_db.commit()

        # Create documents for different users
        client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user1.id),
                "document_type": test_document_type.type_name,
                "title": "User1 Doc",
            },
        )
        client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user2.id),
                "document_type": test_document_type.type_name,
                "title": "User2 Doc",
            },
        )

        # Filter by user1
        response = client.get(f"/api/v1/documents/?user_id={user1.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == str(user1.id)


class TestGetDocument:
    """Test GET /api/v1/documents/{document_id}."""

    def test_get_document_success(self, client, test_user, test_document_type):
        """Test successful document retrieval."""
        # Create a document
        create_response = client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Test Document",
            },
        )
        document_id = create_response.json()["id"]

        # Get the document
        response = client.get(f"/api/v1/documents/{document_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["title"] == "Test Document"

    def test_get_document_not_found(self, client):
        """Test getting non-existent document."""
        random_uuid = str(uuid.uuid4())
        response = client.get(f"/api/v1/documents/{random_uuid}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateDocument:
    """Test PUT /api/v1/documents/{document_id}."""

    def test_update_document_success(self, client, test_user, test_document_type):
        """Test successful document update."""
        # Create a document
        create_response = client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Original Title",
                "status": "draft",
            },
        )
        document_id = create_response.json()["id"]

        # Update the document
        update_data = {"title": "Updated Title", "status": "in_progress"}
        response = client.put(f"/api/v1/documents/{document_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "in_progress"
        assert data["version"] == 2  # Version should increment

    def test_update_document_partial(self, client, test_user, test_document_type):
        """Test partial document update."""
        # Create a document
        create_response = client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Original Title",
                "content_markdown": "Original content",
            },
        )
        document_id = create_response.json()["id"]

        # Update only title
        update_data = {"title": "New Title"}
        response = client.put(f"/api/v1/documents/{document_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["content_markdown"] == "Original content"

    def test_update_document_not_found(self, client):
        """Test updating non-existent document."""
        random_uuid = str(uuid.uuid4())
        update_data = {"title": "New Title"}
        response = client.put(f"/api/v1/documents/{random_uuid}", json=update_data)

        assert response.status_code == 404

    def test_update_document_invalid_status(self, client, test_user, test_document_type):
        """Test updating document with invalid status."""
        # Create a document
        create_response = client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Test Document",
            },
        )
        document_id = create_response.json()["id"]

        # Try to update with invalid status
        update_data = {"status": "invalid_status"}
        response = client.put(f"/api/v1/documents/{document_id}", json=update_data)

        assert response.status_code == 422


class TestDeleteDocument:
    """Test DELETE /api/v1/documents/{document_id}."""

    def test_delete_document_success(self, client, test_user, test_document_type):
        """Test successful document deletion."""
        # Create a document
        create_response = client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Document to Delete",
            },
        )
        document_id = create_response.json()["id"]

        # Delete the document
        response = client.delete(f"/api/v1/documents/{document_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/v1/documents/{document_id}")
        assert get_response.status_code == 404

    def test_delete_document_not_found(self, client):
        """Test deleting non-existent document."""
        random_uuid = str(uuid.uuid4())
        response = client.delete(f"/api/v1/documents/{random_uuid}")

        assert response.status_code == 404


class TestDocumentVersioning:
    """Test document version behavior."""

    def test_version_increments_on_update(self, client, test_user, test_document_type):
        """Test that version increments with each update."""
        # Create a document
        create_response = client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "Version Test",
            },
        )
        document_id = create_response.json()["id"]
        assert create_response.json()["version"] == 1

        # Update 1
        response = client.put(f"/api/v1/documents/{document_id}", json={"title": "Update 1"})
        assert response.json()["version"] == 2

        # Update 2
        response = client.put(f"/api/v1/documents/{document_id}", json={"title": "Update 2"})
        assert response.json()["version"] == 3

    def test_new_document_starts_at_version_1(self, client, test_user, test_document_type):
        """Test that new documents start at version 1."""
        response = client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(test_user.id),
                "document_type": test_document_type.type_name,
                "title": "New Document",
            },
        )

        assert response.status_code == 201
        assert response.json()["version"] == 1
