"""Relationship CRUD API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.v1.models.relationship import (
    AncestorResponse,
    AncestorsResponse,
    BreadcrumbItem,
    BreadcrumbResponse,
    ContextResponse,
    DescendantResponse,
    DescendantsResponse,
    MarkDescendantsResponse,
    RelationshipCreate,
    RelationshipResponse,
)
from src.services.relationship_service import RelationshipService

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.post(
    "/",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new relationship",
)
def create_relationship(
    relationship: RelationshipCreate,
    db: Session = Depends(get_db),
) -> RelationshipResponse:
    """
    Create a new parent-child relationship between documents.

    Validates:
    - Both documents exist
    - No circular dependency
    - Relationship type is allowed
    - No duplicate relationship

    Args:
        relationship: Relationship data
        db: Database session

    Returns:
        Created relationship

    Raises:
        HTTPException: 400 if validation fails, 500 if creation fails
    """
    service = RelationshipService(db)
    try:
        rel = service.create_relationship(
            parent_id=relationship.parent_id,
            child_id=relationship.child_id,
            relationship_type=relationship.relationship_type,
        )
        return RelationshipResponse.model_validate(rel)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create relationship: {str(e)}",
        ) from e


@router.get(
    "/{relationship_id}",
    response_model=RelationshipResponse,
    summary="Get relationship by ID",
)
def get_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db),
) -> RelationshipResponse:
    """
    Get a relationship by ID.

    Args:
        relationship_id: Relationship UUID
        db: Database session

    Returns:
        Relationship

    Raises:
        HTTPException: 404 if not found
    """
    from src.database.models.document_relationship import DocumentRelationship

    rel = db.get(DocumentRelationship, relationship_id)
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found",
        )
    return RelationshipResponse.model_validate(rel)


@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete relationship",
)
def delete_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a relationship.

    Args:
        relationship_id: Relationship UUID
        db: Database session

    Raises:
        HTTPException: 404 if not found
    """
    from src.database.models.document_relationship import DocumentRelationship

    rel = db.get(DocumentRelationship, relationship_id)
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found",
        )

    db.delete(rel)
    db.commit()


@router.get(
    "/documents/{document_id}/breadcrumb",
    response_model=BreadcrumbResponse,
    summary="Get document breadcrumb",
)
def get_document_breadcrumb(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> BreadcrumbResponse:
    """
    Get breadcrumb trail from root to document.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Breadcrumb trail with hierarchy path

    Raises:
        HTTPException: 404 if document not found
    """
    service = RelationshipService(db)
    try:
        breadcrumb_data = service.get_breadcrumb_with_details(document_id)
        breadcrumb_items = [
            BreadcrumbItem(
                id=item["id"],
                title=item["title"],
                document_type=item["document_type"],
            )
            for item in breadcrumb_data
        ]
        breadcrumb_string = service.get_breadcrumb(document_id)
        return BreadcrumbResponse(
            document_id=document_id,
            breadcrumb=breadcrumb_items,
            breadcrumb_string=breadcrumb_string,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/documents/{document_id}/context",
    response_model=ContextResponse,
    summary="Get parent context for RAG",
)
def get_parent_context(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> ContextResponse:
    """
    Get aggregated parent context for RAG.

    Combines content from all ancestor documents to provide
    context for AI-powered operations.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Aggregated parent context

    Raises:
        HTTPException: 404 if document not found
    """
    service = RelationshipService(db)
    try:
        context = service.get_parent_context(document_id)
        ancestors = service.get_ancestors(document_id)
        return ContextResponse(
            document_id=document_id,
            context=context,
            parent_count=len(ancestors),
            total_chars=len(context),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/documents/{document_id}/mark-descendants",
    response_model=MarkDescendantsResponse,
    summary="Mark descendants for review",
)
def mark_descendants_for_review(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> MarkDescendantsResponse:
    """
    Mark all descendants for review (ripple effect).

    When a document changes, all downstream documents should be
    reviewed to ensure consistency.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Count and list of marked documents

    Raises:
        HTTPException: 404 if document not found
    """
    service = RelationshipService(db)
    try:
        marked_ids = service.mark_descendants_for_review(document_id)
        return MarkDescendantsResponse(
            document_id=document_id,
            marked_count=len(marked_ids),
            marked_documents=marked_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/documents/{document_id}/ancestors",
    response_model=AncestorsResponse,
    summary="Get document ancestors",
)
def get_document_ancestors(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> AncestorsResponse:
    """
    Get all ancestor documents in hierarchy.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        List of ancestor documents with hierarchy levels

    Raises:
        HTTPException: 404 if document not found
    """
    service = RelationshipService(db)
    try:
        ancestors_tuples = service.get_ancestors(document_id)
        # Convert tuples to response models
        ancestors = [
            AncestorResponse(
                id=doc.id,
                title=doc.title,
                document_type=doc.document_type,
                level=level,
            )
            for doc, _, level in ancestors_tuples
        ]
        return AncestorsResponse(
            document_id=document_id,
            ancestors=ancestors,
            total=len(ancestors),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/documents/{document_id}/descendants",
    response_model=DescendantsResponse,
    summary="Get document descendants",
)
def get_document_descendants(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> DescendantsResponse:
    """
    Get all descendant documents in hierarchy.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        List of descendant documents with hierarchy levels

    Raises:
        HTTPException: 404 if document not found
    """
    service = RelationshipService(db)
    try:
        descendants_tuples = service.get_descendants(document_id)
        # Convert tuples to response models
        descendants = [
            DescendantResponse(
                id=doc.id,
                title=doc.title,
                document_type=doc.document_type,
                level=level,
            )
            for doc, _, level in descendants_tuples
        ]
        return DescendantsResponse(
            document_id=document_id,
            descendants=descendants,
            total=len(descendants),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
