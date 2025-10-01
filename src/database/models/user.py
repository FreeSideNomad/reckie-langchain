"""
User model for authentication and user management.

Represents users in the system with different roles:
- user: Regular user who can create documents
- admin: Administrator with full system access
- qa_lead: QA lead who creates testing documents
- ddd_designer: Domain-driven design specialist
"""

import uuid
from typing import List, TYPE_CHECKING

from sqlalchemy import String, event
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.document import Document


class User(Base, TimestampMixin):
    """
    User model for authentication and authorization.

    Attributes:
        id: UUID primary key
        username: Unique username for login
        email: Unique email address
        password_hash: Hashed password (never store plain text!)
        role: User role (user, admin, qa_lead, ddd_designer)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        documents: List of documents owned by this user
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key generated on insert"
    )

    # User Information
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username for login"
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique email address"
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password (bcrypt)"
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
        comment="User role: user, admin, qa_lead, ddd_designer"
    )

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="user",
        foreign_keys="[Document.user_id]",
        cascade="all, delete-orphan"
    )

    # Validators
    @validates("email")
    def validate_email(self, key: str, email: str) -> str:
        """
        Validate email format.

        Args:
            key: Field name (automatically provided by SQLAlchemy)
            email: Email address to validate

        Returns:
            Validated email address

        Raises:
            ValueError: If email format is invalid
        """
        if "@" not in email or "." not in email.split("@")[1]:
            raise ValueError(f"Invalid email format: {email}")
        return email.lower()

    @validates("role")
    def validate_role(self, key: str, role: str) -> str:
        """
        Validate role is in allowed list.

        Args:
            key: Field name (automatically provided by SQLAlchemy)
            role: Role to validate

        Returns:
            Validated role

        Raises:
            ValueError: If role is not in allowed list
        """
        allowed_roles = ["user", "admin", "qa_lead", "ddd_designer"]
        if role not in allowed_roles:
            raise ValueError(
                f"Invalid role: {role}. Must be one of {allowed_roles}"
            )
        return role

    def __repr__(self) -> str:
        """String representation showing username and role."""
        return f"User(id={self.id}, username='{self.username}', role='{self.role}')"


# Event listener to ensure email is always lowercase
@event.listens_for(User.email, "set", retval=True)
def lowercase_email(target, value, oldvalue, initiator):
    """Ensure email is always stored in lowercase."""
    if value is not None:
        return value.lower()
    return value
