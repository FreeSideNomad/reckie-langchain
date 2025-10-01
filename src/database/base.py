"""
SQLAlchemy base model with common functionality.

Provides:
- Base declarative class for all models
- Common methods: to_dict(), __repr__()
- Timestamp mixin functionality
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides common functionality:
    - to_dict(): Convert model to dictionary for JSON serialization
    - __repr__(): String representation for debugging

    Usage:
        class User(Base):
            __tablename__ = "users"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            Dictionary with column names as keys and values as values.
            Handles datetime objects by converting to ISO format strings.

        Example:
            user = User(id=1, username="john")
            user.to_dict()  # {"id": 1, "username": "john"}
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)

            # Convert datetime to ISO format string
            if isinstance(value, datetime):
                value = value.isoformat()

            result[column.name] = value

        return result

    def __repr__(self) -> str:
        """
        String representation of model instance.

        Returns:
            String in format: ClassName(id=1, name='value', ...)

        Example:
            repr(user)  # "User(id=1, username='john')"
        """
        # Get primary key columns
        pk_columns = [col.name for col in self.__table__.primary_key.columns]

        # Build key=value pairs for primary keys
        pk_values = []
        for col_name in pk_columns:
            value = getattr(self, col_name, None)
            if isinstance(value, str):
                pk_values.append(f"{col_name}='{value}'")
            else:
                pk_values.append(f"{col_name}={value}")

        return f"{self.__class__.__name__}({', '.join(pk_values)})"


class TimestampMixin:
    """
    Mixin for models that need created_at and updated_at timestamps.

    Provides:
    - created_at: Timestamp when record was created (auto-set on insert)
    - updated_at: Timestamp when record was last updated (auto-updated)

    Usage:
        class User(Base, TimestampMixin):
            __tablename__ = "users"
            id: Mapped[int] = mapped_column(primary_key=True)

    Note: Database trigger is required for auto-updating updated_at.
    See migrations for trigger creation (update_updated_at_column).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp (UTC, auto-updated by trigger)",
    )
