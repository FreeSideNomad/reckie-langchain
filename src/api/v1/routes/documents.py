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
from src.database.models.document import Document

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
