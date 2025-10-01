"""
Tests for DocumentEmbedding model.

Tests:
- Model creation and validation
- Chunk validation
- JSONB metadata operations
- Helper methods
- Relationships
"""

import pytest
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.database.base import Base
from src.database.models.user import User
from src.database.models.document_type import DocumentType
from src.database.models.document import Document
from src.database.models.document_embedding import DocumentEmbedding


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def user(session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hash",
        role="user"
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def doc_type(session):
    """Create a test document type."""
    doc_type = DocumentType(
        type_name="test_type",
        system_prompt="Test",
        workflow_steps=[]
    )
    session.add(doc_type)
    session.commit()
    return doc_type


@pytest.fixture
def document(session, user, doc_type):
    """Create a test document."""
    document = Document(
        user_id=user.id,
        document_type=doc_type.type_name,
        title="Test Document"
    )
    session.add(document)
    session.commit()
    return document


class TestDocumentEmbeddingModel:
    """Test DocumentEmbedding model functionality."""

    def test_create_embedding(self, session, document):
        """Test creating a document embedding."""
        embedding = DocumentEmbedding(
            document_id=document.id,
            chunk_text="This is a test chunk of text",
            chunk_index=0,
            chunk_metadata={"tokens": 10}
        )
        session.add(embedding)
        session.commit()

        assert embedding.id is not None
        assert embedding.document_id == document.id
        assert embedding.chunk_text == "This is a test chunk of text"
        assert embedding.chunk_index == 0
        assert embedding.chunk_metadata == {"tokens": 10}

    def test_chunk_index_validation(self):
        """Test chunk_index must be non-negative."""
        with pytest.raises(ValueError, match="Chunk index must be >= 0"):
            DocumentEmbedding(
                document_id=uuid.uuid4(),
                chunk_text="Test",
                chunk_index=-1
            )

    def test_chunk_text_validation(self):
        """Test chunk_text cannot be empty."""
        with pytest.raises(ValueError, match="Chunk text cannot be empty"):
            DocumentEmbedding(
                document_id=uuid.uuid4(),
                chunk_text="",
                chunk_index=0
            )

    def test_chunk_text_whitespace_validation(self):
        """Test chunk_text cannot be only whitespace."""
        with pytest.raises(ValueError, match="Chunk text cannot be empty"):
            DocumentEmbedding(
                document_id=uuid.uuid4(),
                chunk_text="   ",
                chunk_index=0
            )

    def test_unique_document_chunk_constraint(self, session, document):
        """Test unique constraint on (document_id, chunk_index)."""
        emb1 = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Chunk 1",
            chunk_index=0
        )
        session.add(emb1)
        session.commit()

        emb2 = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Chunk 1 duplicate",
            chunk_index=0
        )
        session.add(emb2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_multiple_chunks_same_document(self, session, document):
        """Test multiple chunks for same document with different indices."""
        emb1 = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Chunk 1",
            chunk_index=0
        )
        emb2 = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Chunk 2",
            chunk_index=1
        )
        emb3 = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Chunk 3",
            chunk_index=2
        )
        session.add_all([emb1, emb2, emb3])
        session.commit()

        # Verify all chunks created
        assert emb1.chunk_index == 0
        assert emb2.chunk_index == 1
        assert emb3.chunk_index == 2

    def test_get_metadata_value(self, session, document):
        """Test get_metadata_value helper."""
        embedding = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Test",
            chunk_index=0,
            chunk_metadata={"tokens": 50, "overlap": 10}
        )
        session.add(embedding)
        session.commit()

        assert embedding.get_metadata_value("tokens") == 50
        assert embedding.get_metadata_value("overlap") == 10
        assert embedding.get_metadata_value("missing", "default") == "default"

    def test_set_metadata_value(self, session, document):
        """Test set_metadata_value helper."""
        embedding = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Test",
            chunk_index=0
        )
        session.add(embedding)
        session.commit()

        embedding.set_metadata_value("tokens", 75)
        embedding.set_metadata_value("context", "intro")

        assert embedding.get_metadata_value("tokens") == 75
        assert embedding.get_metadata_value("context") == "intro"

    def test_get_embedding_dimension(self, session, document):
        """Test get_embedding_dimension returns correct dimension."""
        embedding = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Test",
            chunk_index=0
        )
        session.add(embedding)
        session.commit()

        assert embedding.get_embedding_dimension() == 1536

    def test_embedding_repr(self, session, document):
        """Test __repr__ method."""
        embedding = DocumentEmbedding(
            document_id=document.id,
            chunk_text="This is a long chunk of text that will be truncated in the repr output",
            chunk_index=0
        )
        session.add(embedding)
        session.commit()

        repr_str = repr(embedding)
        assert "DocumentEmbedding" in repr_str
        assert str(document.id) in repr_str
        assert "chunk_index=0" in repr_str
        assert "..." in repr_str  # Text truncation

    def test_embedding_relationship(self, session, document):
        """Test relationship between Document and DocumentEmbedding."""
        emb1 = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Chunk 1",
            chunk_index=0
        )
        emb2 = DocumentEmbedding(
            document_id=document.id,
            chunk_text="Chunk 2",
            chunk_index=1
        )
        session.add_all([emb1, emb2])
        session.commit()

        # Test relationship
        assert len(document.embeddings) == 2
        assert emb1.document.title == document.title
        assert emb2.document.title == document.title


def test_cascade_delete(session, user, doc_type):
    """Test cascade delete when document is deleted."""
    document = Document(
        user_id=user.id,
        document_type=doc_type.type_name,
        title="Test Doc"
    )
    session.add(document)
    session.commit()

    emb1 = DocumentEmbedding(
        document_id=document.id,
        chunk_text="Chunk 1",
        chunk_index=0
    )
    emb2 = DocumentEmbedding(
        document_id=document.id,
        chunk_text="Chunk 2",
        chunk_index=1
    )
    session.add_all([emb1, emb2])
    session.commit()

    # Delete document
    session.delete(document)
    session.commit()

    # Embeddings should be deleted due to cascade
    from sqlalchemy import select
    result = session.execute(select(DocumentEmbedding)).scalars().all()
    assert len(result) == 0
