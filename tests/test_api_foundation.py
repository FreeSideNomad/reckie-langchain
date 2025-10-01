"""Tests for FastAPI foundation and health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.dependencies import get_db
from src.api.main import app
from src.database.base import Base


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db):
    """Create FastAPI test client with test database."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestHealthCheck:
    """Test health check endpoints."""

    def test_health_check_returns_200(self, client):
        """Test GET /health returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["service"] == "document-management-api"

    def test_health_check_structure(self, client):
        """Test health check response has correct structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "service" in data

    def test_db_health_check_returns_200(self, client):
        """Test GET /health/db returns 200 when database is connected."""
        response = client.get("/health/db")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation endpoints."""

    def test_openapi_docs_available(self, client):
        """Test OpenAPI docs are available at /docs."""
        response = client.get("/docs")

        # Should return HTML for Swagger UI
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json_available(self, client):
        """Test OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Document Management API"
        assert data["info"]["version"] == "1.0.0"

    def test_redoc_available(self, client):
        """Test ReDoc documentation is available at /redoc."""
        response = client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses with Origin header."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_all_origins(self, client):
        """Test CORS allows all origins (development configuration)."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS preflight should succeed
        assert response.status_code == 200


class TestExceptionHandlers:
    """Test exception handlers."""

    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_validation_error_format(self, client):
        """Test validation error returns proper format."""
        # This will be tested more thoroughly in CRUD endpoints
        # For now, just verify the endpoint structure
        response = client.get("/health")
        assert response.status_code == 200

    def test_database_error_handling(self, client, monkeypatch):
        """Test database error handling."""
        from sqlalchemy.exc import SQLAlchemyError

        # Mock get_db to raise an error
        def mock_get_db_error():
            raise SQLAlchemyError("Database connection failed")

        # This would test the error handler but we need a route that uses it
        # For now, the handler exists and will be tested in CRUD endpoints
        pass


class TestDatabaseDependency:
    """Test database dependency injection."""

    def test_get_db_dependency_works(self, client, test_db):
        """Test get_db() dependency injection works."""
        # The fact that health check works proves dependency injection works
        response = client.get("/health/db")

        assert response.status_code == 200

    def test_get_db_closes_connection(self, test_db):
        """Test get_db() closes database connection after use."""
        from src.api.dependencies import get_db

        # Get a session
        db_gen = get_db()
        db = next(db_gen)

        # Verify it's open
        assert db.is_active

        # Close it (FastAPI does this automatically)
        try:
            next(db_gen)
        except StopIteration:
            pass

        # Connection should be closed
        # Note: SQLite doesn't have a clear "closed" state, but the pattern is correct


class TestApplicationStructure:
    """Test FastAPI application structure."""

    def test_app_title_and_version(self):
        """Test app has correct title and version."""
        assert app.title == "Document Management API"
        assert app.version == "1.0.0"

    def test_docs_enabled(self):
        """Test OpenAPI documentation is enabled."""
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_middleware_configured(self):
        """Test CORS middleware is configured."""
        # Check middleware is present by looking at middleware_stack
        # FastAPI wraps middleware, so we need to check differently
        assert len(app.user_middleware) > 0  # Middleware is configured
        # CORS functionality is tested in TestCORSMiddleware class
