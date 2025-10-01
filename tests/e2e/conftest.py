"""E2E test configuration with Testcontainers.

This module provides pytest fixtures for end-to-end testing with:
- PostgreSQL + pgvector container (session-scoped for performance)
- Database migrations
- FastAPI TestClient
- Proper container lifecycle management

NOTE: These tests require Docker to be running. If Docker is not available,
tests will be skipped automatically.
"""

import docker
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from src.api.dependencies import get_db
from src.api.main import app
from src.database.base import Base


def is_docker_available():
    """Check if Docker is available and running."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


# Skip all E2E tests if Docker is not available
pytestmark = pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker is not available - E2E tests require Docker to be running",
)


@pytest.fixture(scope="session")
def postgres_container():
    """
    Start PostgreSQL + pgvector container for entire test session.

    This fixture is session-scoped for performance - the container
    starts once and is reused across all E2E tests.

    Yields:
        PostgresContainer: Running container with pgvector extension
    """
    if not is_docker_available():
        pytest.skip("Docker is not available - E2E tests require Docker to be running")

    # Use pgvector/pgvector image with PostgreSQL 15
    with PostgresContainer("pgvector/pgvector:pg15") as postgres:
        # Wait for container to be ready
        postgres.get_connection_url()  # This blocks until ready

        # Run migrations
        engine = create_engine(postgres.get_connection_url())
        Base.metadata.create_all(engine)
        engine.dispose()

        yield postgres


@pytest.fixture
def test_db(postgres_container):
    """
    Create database session for each test.

    Provides a clean database session with automatic rollback
    after each test to ensure test isolation.

    Args:
        postgres_container: PostgreSQL container fixture

    Yields:
        Session: SQLAlchemy database session
    """
    engine = create_engine(postgres_container.get_connection_url())
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    try:
        yield db
    finally:
        db.rollback()  # Rollback changes after test
        db.close()


@pytest.fixture
def api_client(test_db):
    """
    Create FastAPI test client with test database.

    Overrides the get_db dependency to use the test database
    instead of the production database.

    Args:
        test_db: Test database session

    Yields:
        TestClient: FastAPI test client
    """

    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # Cleanup handled by test_db fixture

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    # Clean up dependency overrides
    app.dependency_overrides.clear()
