"""Document CRUD API endpoints."""

from math import ceil
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.v1.models.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
)
from src.api.v1.models.relationship import (
    AncestorResponse,
    AncestorsResponse,
    BreadcrumbItem,
    BreadcrumbResponse,
    ContextResponse,
    DescendantResponse,
    DescendantsResponse,
    MarkDescendantsResponse,
)
from src.database.models.document import Document
from src.services.relationship_service import RelationshipService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new document",
)
def create_document(
    document: DocumentCreate,
    db: Session = Depends(get_db),
) -> Document:
    """
    Create a new document.

    Args:
        document: Document data
        db: Database session

    Returns:
        Created document

    Raises:
        HTTPException: If creation fails
    """
    try:
        db_document = Document(
            user_id=document.user_id,
            document_type=document.document_type,
            title=document.title,
            content_markdown=document.content_markdown,
            domain_model=document.domain_model,
            doc_metadata=document.doc_metadata,
            status=document.status,
            created_by=document.user_id,
            updated_by=document.user_id,
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        return db_document
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents with pagination",
)
def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """
    List documents with pagination and optional filters.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        document_type: Optional document type filter
        status: Optional status filter
        user_id: Optional user ID filter
        db: Database session

    Returns:
        Paginated list of documents
    """
    # Build query with filters
    query = select(Document)

    if document_type:
        query = query.where(Document.document_type == document_type)
    if status:
        query = query.where(Document.status == status)
    if user_id:
        query = query.where(Document.user_id == user_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    documents = list(db.execute(query).scalars().all())

    return DocumentListResponse(
        items=documents,  # type: ignore[arg-type]  # Pydantic converts from ORM
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> Document:
    """
    Get a document by ID.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Document

    Raises:
        HTTPException: If document not found
    """
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    return document


@router.put(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update document",
)
def update_document(
    document_id: UUID,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db),
) -> Document:
    """
    Update a document.

    Args:
        document_id: Document UUID
        document_update: Fields to update
        db: Database session

    Returns:
        Updated document

    Raises:
        HTTPException: If document not found or update fails
    """
    db_document = db.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    try:
        # Update only provided fields
        update_data = document_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_document, field, value)

        # Increment version on update
        db_document.increment_version()

        db.commit()
        db.refresh(db_document)
        return db_document
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {str(e)}",
        ) from e


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a document.

    Args:
        document_id: Document UUID
        db: Database session

    Raises:
        HTTPException: If document not found
    """
    db_document = db.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    db.delete(db_document)
    db.commit()


# Hierarchy and Relationship Endpoints


@router.get(
    "/{document_id}/ancestors",
    response_model=AncestorsResponse,
    summary="Get document ancestors",
    tags=["documents", "hierarchy"],
)
def get_ancestors(
    document_id: UUID,
    max_depth: int = Query(
        default=None, ge=1, le=100, description="Maximum depth to traverse"
    ),  # noqa: B008
    db: Session = Depends(get_db),
) -> AncestorsResponse:
    """
    Get all ancestors (parents, grandparents, etc.) of a document.

    Args:
        document_id: Document UUID
        max_depth: Maximum depth to traverse (optional)
        db: Database session

    Returns:
        List of ancestors with hierarchy levels

    Raises:
        HTTPException: 404 if document not found
    """
    # Verify document exists
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    service = RelationshipService(db)
    ancestors_data = service.get_ancestors(document_id, max_depth=max_depth)

    ancestors = [
        AncestorResponse(
            id=doc.id,
            title=doc.title,
            document_type=doc.document_type,
            level=depth,
        )
        for doc, _relationship_type, depth in ancestors_data
    ]

    return AncestorsResponse(
        document_id=document_id,
        ancestors=ancestors,
        total=len(ancestors),
    )


@router.get(
    "/{document_id}/descendants",
    response_model=DescendantsResponse,
    summary="Get document descendants",
    tags=["documents", "hierarchy"],
)
def get_descendants(
    document_id: UUID,
    max_depth: int = Query(
        default=None, ge=1, le=100, description="Maximum depth to traverse"
    ),  # noqa: B008
    db: Session = Depends(get_db),
) -> DescendantsResponse:
    """
    Get all descendants (children, grandchildren, etc.) of a document.

    Args:
        document_id: Document UUID
        max_depth: Maximum depth to traverse (optional)
        db: Database session

    Returns:
        List of descendants with hierarchy levels

    Raises:
        HTTPException: 404 if document not found
    """
    # Verify document exists
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    service = RelationshipService(db)
    descendants_data = service.get_descendants(document_id, max_depth=max_depth)

    descendants = [
        DescendantResponse(
            id=doc.id,
            title=doc.title,
            document_type=doc.document_type,
            level=depth,
        )
        for doc, _relationship_type, depth in descendants_data
    ]

    return DescendantsResponse(
        document_id=document_id,
        descendants=descendants,
        total=len(descendants),
    )


@router.get(
    "/{document_id}/breadcrumb",
    response_model=BreadcrumbResponse,
    summary="Get document breadcrumb",
    tags=["documents", "hierarchy"],
)
def get_breadcrumb(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> BreadcrumbResponse:
    """
    Get breadcrumb trail from root to document.

    Example: Vision > Feature > Epic > User Story

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Breadcrumb trail with document titles

    Raises:
        HTTPException: 404 if document not found
    """
    # Verify document exists
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    service = RelationshipService(db)
    breadcrumb_data = service.get_breadcrumb_with_details(document_id)

    breadcrumb = [
        BreadcrumbItem(
            id=item["id"],
            title=item["title"],
            document_type=item["document_type"],
        )
        for item in breadcrumb_data
    ]

    # Create human-readable string
    breadcrumb_string = " > ".join(item.title for item in breadcrumb)

    return BreadcrumbResponse(
        document_id=document_id,
        breadcrumb=breadcrumb,
        breadcrumb_string=breadcrumb_string,
    )


@router.get(
    "/{document_id}/context",
    response_model=ContextResponse,
    summary="Get parent context for RAG",
    tags=["documents", "hierarchy"],
)
def get_parent_context(
    document_id: UUID,
    max_chars_per_parent: int = Query(  # noqa: B008
        default=2000,
        ge=100,
        le=10000,
        description="Maximum characters per parent document",
    ),
    db: Session = Depends(get_db),
) -> ContextResponse:
    """
    Get aggregated parent context for RAG (Retrieval-Augmented Generation).

    Combines markdown content from all ancestor documents for use in
    LLM prompts to provide hierarchical context.

    Args:
        document_id: Document UUID
        max_chars_per_parent: Maximum characters to include per parent (default: 2000)
        db: Database session

    Returns:
        Aggregated parent context

    Raises:
        HTTPException: 404 if document not found
    """
    # Verify document exists
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    service = RelationshipService(db)
    context = service.get_parent_context(
        document_id=document_id,
        max_chars_per_parent=max_chars_per_parent,
    )

    # Count parent documents
    ancestors = service.get_ancestors(document_id)
    parent_count = len(ancestors)

    return ContextResponse(
        document_id=document_id,
        context=context,
        parent_count=parent_count,
        total_chars=len(context),
    )


@router.post(
    "/{document_id}/mark-descendants",
    response_model=MarkDescendantsResponse,
    summary="Mark descendants for review (ripple effect)",
    tags=["documents", "hierarchy"],
)
def mark_descendants_for_review(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> MarkDescendantsResponse:
    """
    Mark all descendant documents as needing review (ripple effect).

    When a parent document is updated, this endpoint marks all children,
    grandchildren, etc. as 'stale' to indicate they need review.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Count and list of marked documents

    Raises:
        HTTPException: 404 if document not found
    """
    # Verify document exists
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    service = RelationshipService(db)
    marked_ids = service.mark_descendants_for_review(document_id)

    return MarkDescendantsResponse(
        document_id=document_id,
        marked_count=len(marked_ids),
        marked_documents=marked_ids,
    )
