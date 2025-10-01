"""Pydantic models for Document CRUD API."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DocumentBase(BaseModel):
    """Base model for Document with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    document_type: str = Field(
        ..., min_length=1, max_length=100, description="Document type identifier"
    )
    content_markdown: Optional[str] = Field(None, description="Rendered markdown content")
    domain_model: Dict[str, Any] = Field(
        default_factory=dict, description="YAML domain model as JSONB"
    )
    doc_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (tags, priority, etc.)"
    )
    status: str = Field(
        default="draft",
        description="Document lifecycle status: draft, in_progress, complete, stale",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is in allowed list."""
        allowed_statuses = ["draft", "in_progress", "complete", "stale"]
        if v not in allowed_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {allowed_statuses}")
        return v


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""

    user_id: UUID = Field(..., description="Owner user ID")


class DocumentUpdate(BaseModel):
    """Model for updating an existing document (all fields optional)."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content_markdown: Optional[str] = None
    domain_model: Optional[Dict[str, Any]] = None
    doc_metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status is in allowed list."""
        if v is not None:
            allowed_statuses = ["draft", "in_progress", "complete", "stale"]
            if v not in allowed_statuses:
                raise ValueError(f"Invalid status: {v}. Must be one of {allowed_statuses}")
        return v


class DocumentResponse(DocumentBase):
    """Model for document response."""

    id: UUID
    user_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentListResponse(BaseModel):
    """Model for paginated document list response."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
