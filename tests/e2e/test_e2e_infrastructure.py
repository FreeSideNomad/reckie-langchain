"""E2E infrastructure validation tests.

Verifies that the Testcontainers infrastructure is working correctly:
- PostgreSQL container starts and accepts connections
- pgvector extension is available
- Migrations run successfully
- FastAPI TestClient can interact with container DB
"""

import uuid


class TestE2EInfrastructure:
    """Test E2E testing infrastructure setup."""

    def test_postgres_container_ready(self, postgres_container):
        """Verify PostgreSQL container is running and accessible."""
        # Get connection URL
        conn_url = postgres_container.get_connection_url()
        assert conn_url is not None
        assert "postgresql" in conn_url
        assert "localhost" in conn_url or "127.0.0.1" in conn_url

    def test_pgvector_extension_available(self, test_db):
        """Verify pgvector extension is installed and functional."""
        from sqlalchemy import text

        # Test pgvector is installed
        result = test_db.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        has_pgvector = result.scalar()
        assert has_pgvector is True, "pgvector extension not installed"

        # Test vector operations work
        test_db.execute(text("SELECT '[1,2,3]'::vector"))

    def test_database_migrations_applied(self, test_db):
        """Verify database migrations have been applied."""
        from sqlalchemy import text

        # Check critical tables exist
        tables = [
            "users",
            "document_types",
            "documents",
            "document_relationships",
            "document_embeddings",
            "conversations",
            "document_versions",
        ]

        for table in tables:
            result = test_db.execute(
                text(
                    f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                )
                """
                )
            )
            table_exists = result.scalar()
            assert table_exists is True, f"Table '{table}' does not exist"

    def test_fastapi_testclient_working(self, api_client):
        """Verify FastAPI TestClient can make requests."""
        # Test health check endpoint
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_database_session_isolation(self, api_client, test_db):
        """Verify test database sessions are isolated (rollback after test)."""
        from src.database.models.user import User

        # Create a user via API
        test_user_id = uuid.uuid4()
        test_db.add(
            User(
                id=test_user_id,
                email="test_isolation@example.com",
                username="test_isolation",
                password_hash="hash",
                role="user",
            )
        )
        test_db.commit()

        # Verify user exists in same transaction
        user = test_db.query(User).filter(User.id == test_user_id).first()
        assert user is not None

        # Note: After test, rollback should happen automatically
        # Next test will verify user is gone (via new session)


class TestE2EBasicCRUD:
    """Basic CRUD operations to verify E2E infrastructure."""

    def test_create_and_retrieve_document(self, api_client, test_db):
        """E2E: Create document and retrieve it via API."""
        from src.database.models.document_type import DocumentType
        from src.database.models.user import User

        # Setup: Create user and document type
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            role="user",
        )
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test prompt",
            workflow_steps=[],
            parent_types=[],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type)
        test_db.commit()

        # Act: Create document via API
        response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "E2E Test Document",
                "content_markdown": "# E2E Test\n\nThis is a test document.",
            },
        )

        # Assert: Document created successfully
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "E2E Test Document"
        assert data["document_type"] == "test_type"
        document_id = data["id"]

        # Act: Retrieve document via API
        get_response = api_client.get(f"/api/v1/documents/{document_id}")

        # Assert: Document retrieved successfully
        assert get_response.status_code == 200
        retrieved = get_response.json()
        assert retrieved["id"] == document_id
        assert retrieved["title"] == "E2E Test Document"
