"""Pydantic models for Relationship API endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RelationshipCreate(BaseModel):
    """Model for creating a new relationship."""

    parent_id: UUID = Field(..., description="Parent document UUID")
    child_id: UUID = Field(..., description="Child document UUID")
    relationship_type: str = Field(default="parent_child", description="Type of relationship")


class RelationshipResponse(BaseModel):
    """Model for relationship response."""

    id: UUID
    parent_id: UUID
    child_id: UUID
    relationship_type: str
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class AncestorResponse(BaseModel):
    """Model for single ancestor in hierarchy."""

    id: UUID
    title: str
    document_type: str
    level: int = Field(description="Distance from original document (1 = immediate parent)")


class AncestorsResponse(BaseModel):
    """Model for ancestors list response."""

    document_id: UUID
    ancestors: list[AncestorResponse]
    total: int


class DescendantResponse(BaseModel):
    """Model for single descendant in hierarchy."""

    id: UUID
    title: str
    document_type: str
    level: int = Field(description="Distance from original document (1 = immediate child)")


class DescendantsResponse(BaseModel):
    """Model for descendants list response."""

    document_id: UUID
    descendants: list[DescendantResponse]
    total: int


class BreadcrumbItem(BaseModel):
    """Model for single breadcrumb item."""

    id: UUID
    title: str
    document_type: str


class BreadcrumbResponse(BaseModel):
    """Model for breadcrumb response."""

    document_id: UUID
    breadcrumb: list[BreadcrumbItem]
    breadcrumb_string: str = Field(description="Human-readable breadcrumb path")


class ContextResponse(BaseModel):
    """Model for parent context response."""

    document_id: UUID
    context: str = Field(description="Aggregated parent context for RAG")
    parent_count: int
    total_chars: int


class MarkDescendantsResponse(BaseModel):
    """Model for mark descendants response."""

    document_id: UUID
    marked_count: int
    marked_documents: list[UUID] = Field(description="List of marked document IDs")
