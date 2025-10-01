"""
Database connection and session management.

Provides:
- engine: SQLAlchemy engine with connection pooling
- SessionLocal: Session factory for creating database sessions
- get_db: Dependency for FastAPI route handlers

Environment Variables:
- DATABASE_URL: PostgreSQL connection string
  Format: postgresql://user:password@host:port/database
  Example: postgresql://langchain_user:password@localhost:5432/langchain_docs
"""

import os
from typing import Any, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://langchain_user:changeme@localhost:5432/langchain_docs"
)

# Create engine with connection pooling
# QueuePool configuration:
# - pool_size: Number of connections to maintain (default: 5)
# - max_overflow: Additional connections when pool is full (default: 10)
# - pool_timeout: Seconds to wait for connection before raising error (default: 30)
# - pool_recycle: Recycle connections after N seconds to prevent stale connections (3600 = 1 hour)
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Log SQL queries if SQL_ECHO=true
)


# Enable connection pool statistics logging
@event.listens_for(Engine, "connect")
def receive_connect(dbapi_conn: Any, connection_record: Any) -> None:
    """Log database connections for monitoring."""
    # This can be extended with logging if needed
    pass


@event.listens_for(Engine, "checkout")
def receive_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
    """Track connection checkout for debugging pool exhaustion."""
    # This can be extended with logging/metrics if needed
    pass


# Session factory
# expire_on_commit=False: Don't expire objects after commit (allows accessing them after commit)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI route handlers to get database session.

    Yields a database session and ensures it's closed after use.
    Automatically rolls back on exception.

    Usage in FastAPI:
        from fastapi import Depends
        from src.database import get_db

        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()

    Yields:
        Session: SQLAlchemy database session

    Example:
        with get_db() as db:
            users = db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit if no exceptions
    except Exception:
        db.rollback()  # Rollback on any exception
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This is primarily for testing. In production, use Alembic migrations.

    Usage:
        from src.database.connection import init_db
        init_db()  # Creates all tables defined in models
    """
    from src.database.base import Base

    # Import all models here so they're registered with Base
    # This will be populated as we create models
    # from src.database.models import user, document, document_type, etc.

    Base.metadata.create_all(bind=engine)


def drop_all() -> None:
    """
    Drop all tables from database.

    WARNING: This will delete all data. Only use for testing.

    Usage:
        from src.database.connection import drop_all
        drop_all()  # Drops all tables
    """
    from src.database.base import Base

    Base.metadata.drop_all(bind=engine)


def get_db_info() -> dict:
    """
    Get database connection information for diagnostics.

    Returns:
        Dictionary with connection details (URL without password, pool stats)

    Example:
        info = get_db_info()
        print(f"Connected to: {info['database']}")
        print(f"Pool size: {info['pool_size']}")
    """
    # Parse DATABASE_URL to hide password
    from urllib.parse import urlparse

    parsed = urlparse(DATABASE_URL)
    safe_url = (
        f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
    )

    pool = engine.pool

    return {
        "database_url": safe_url,
        "database": parsed.path.lstrip("/"),
        "host": parsed.hostname,
        "port": parsed.port,
        "pool_size": pool.size(),  # type: ignore
        "checked_out_connections": pool.checkedout(),  # type: ignore
        "overflow": pool.overflow(),  # type: ignore
        "pool_timeout": pool._timeout,  # type: ignore
    }
