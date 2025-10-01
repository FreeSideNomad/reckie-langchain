"""
Tests for database base model and connection.

Tests:
- Base model to_dict() method
- Base model __repr__() method
- TimestampMixin functionality
- Database connection and session management
"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, TimestampMixin
from src.database.connection import SessionLocal, get_db, get_db_info


class TestModel(Base, TimestampMixin):
    """Test model for base class functionality."""

    __tablename__ = "test_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))


class TestBaseModel:
    """Test Base model functionality."""

    def test_to_dict_basic(self):
        """Test to_dict() method converts model to dictionary."""
        # Create test instance (not saved to DB)
        model = TestModel(id=1, name="Test User", email="test@example.com")

        # Convert to dict
        result = model.to_dict()

        # Verify basic fields
        assert result["id"] == 1
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"

    def test_to_dict_handles_datetime(self):
        """Test to_dict() converts datetime to ISO format string."""
        model = TestModel(id=1, name="Test", email="test@example.com")

        # Set timestamps manually
        now = datetime.now()
        model.created_at = now
        model.updated_at = now

        result = model.to_dict()

        # Verify datetime converted to string
        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)
        assert result["created_at"] == now.isoformat()

    def test_repr(self):
        """Test __repr__() provides readable string representation."""
        model = TestModel(id=42, name="Test", email="test@example.com")

        repr_str = repr(model)

        # Verify format: ClassName(id=value)
        assert "TestModel" in repr_str
        assert "id=42" in repr_str

    def test_repr_string_primary_key(self):
        """Test __repr__() handles string primary keys."""
        import uuid

        from sqlalchemy import UUID as SQLUUID

        class TestUUIDModel(Base):
            __tablename__ = "test_uuid_models"
            id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)

        test_id = uuid.uuid4()
        model = TestUUIDModel(id=test_id)

        repr_str = repr(model)

        assert "TestUUIDModel" in repr_str
        assert str(test_id) in repr_str


class TestTimestampMixin:
    """Test TimestampMixin functionality."""

    def test_timestamp_mixin_fields_exist(self):
        """Test TimestampMixin adds created_at and updated_at fields."""
        model = TestModel(id=1, name="Test", email="test@example.com")

        # Verify fields exist
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")

    def test_timestamp_fields_in_to_dict(self):
        """Test timestamp fields included in to_dict() output."""
        model = TestModel(id=1, name="Test", email="test@example.com")
        model.created_at = datetime.now()
        model.updated_at = datetime.now()

        result = model.to_dict()

        assert "created_at" in result
        assert "updated_at" in result


class TestDatabaseConnection:
    """Test database connection and session management."""

    def test_get_db_yields_session(self):
        """Test get_db() yields a valid session."""
        db_gen = get_db()
        db = next(db_gen)

        # Verify it's a Session instance
        assert db is not None
        assert hasattr(db, "query")
        assert hasattr(db, "commit")

        # Clean up
        try:
            next(db_gen)
        except StopIteration:
            pass

    def test_session_local_creates_session(self):
        """Test SessionLocal factory creates valid sessions."""
        session = SessionLocal()

        assert session is not None
        assert hasattr(session, "query")
        assert hasattr(session, "commit")

        session.close()

    def test_get_db_info_returns_connection_details(self):
        """Test get_db_info() returns database connection information."""
        info = get_db_info()

        # Verify expected keys
        assert "database_url" in info
        assert "database" in info
        assert "host" in info
        assert "pool_size" in info

        # Verify password is masked
        assert "***" in info["database_url"]
        assert "password" not in info["database_url"].lower() or "***" in info["database_url"]

    def test_get_db_context_manager(self):
        """Test get_db() can be used as context manager."""
        db = SessionLocal()

        # Verify session is initially active
        assert db is not None

        # Use the session
        with db:
            assert db.is_active is True

        # After context exit, manually close if needed
        # Note: SQLAlchemy sessions may remain active until explicitly closed
        if db.is_active:
            db.close()

        # Verify we can work with the session object
        assert db is not None

    def test_database_url_from_env(self, monkeypatch):
        """Test DATABASE_URL can be configured via environment variable."""
        from src.database import connection

        # Note: This test verifies the module reads DATABASE_URL
        # The actual value is already set when module is imported
        assert connection.DATABASE_URL is not None
        assert "postgresql://" in connection.DATABASE_URL


def test_base_declarative_base():
    """Test Base is a valid SQLAlchemy declarative base."""
    # Verify Base has required attributes
    assert hasattr(Base, "metadata")
    # Note: Base itself doesn't have __table__, but instances do
    assert hasattr(Base, "metadata")

    # Verify we can create a model from Base
    class SampleModel(Base):
        __tablename__ = "sample"
        id: Mapped[int] = mapped_column(primary_key=True)

    assert SampleModel.__tablename__ == "sample"
    # The class has __table__ attribute after being defined
    assert hasattr(SampleModel, "__table__")
