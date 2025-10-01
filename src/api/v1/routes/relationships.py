"""Relationship CRUD API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.v1.models.relationship import (
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
