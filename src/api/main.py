"""FastAPI application entry point."""

from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from src.api.dependencies import get_db
from src.api.v1.routes.documents import router as documents_router
from src.api.v1.routes.relationships import router as relationships_router

# Create FastAPI app
app = FastAPI(
    title="Document Management API",
    description="AI-Powered Hierarchical Document Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents_router, prefix="/api/v1")
app.include_router(relationships_router, prefix="/api/v1")


# Exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred", "error": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    # Convert errors to JSON-serializable format (exclude ctx with exception objects)
    errors = []
    for error in exc.errors():
        error_dict = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": error.get("input"),
        }
        errors.append(error_dict)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# Health check endpoint
@app.get("/health", tags=["health"])
def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: Health status and version info
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "document-management-api",
    }


# Database health check
@app.get("/health/db", tags=["health"], response_model=None)
def health_check_db() -> Union[dict, JSONResponse]:
    """
    Database health check endpoint.

    Returns:
        dict: Database connection status

    Raises:
        HTTPException: If database connection fails
    """
    from sqlalchemy import text

    db = next(get_db())
    try:
        # Simple query to check connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )
    finally:
        db.close()
