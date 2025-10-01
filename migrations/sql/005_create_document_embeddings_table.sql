-- ==========================================
-- Migration: 005_create_document_embeddings_table
-- User Story: US-F1-E2-S5
-- Description: Create document_embeddings table for vector embeddings storage
-- Dependencies: documents table (003), pgvector extension (001)
-- ==========================================

-- ==========================================
-- Document Embeddings Table
-- ==========================================
-- Purpose: Store vector embeddings for RAG-powered context retrieval
-- Documents are chunked into 500-token segments, embedded with OpenAI
-- Enables semantic search and relevant context injection into AI prompts
-- ==========================================

CREATE TABLE IF NOT EXISTS document_embeddings (
    -- Primary identifier using UUID v4
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Document reference (foreign key to documents)
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Chunk text (the actual text segment that was embedded)
    chunk_text TEXT NOT NULL,

    -- Chunk index (order within document, 0-based)
    chunk_index INTEGER NOT NULL,

    -- Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)
    embedding vector(1536) NOT NULL,

    -- Metadata as JSONB
    -- Format: {chunk_size: 500, section_title: "...", token_count: 123}
    metadata JSONB DEFAULT '{}',

    -- Audit timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    -- Ensure unique chunk index per document
    CONSTRAINT uq_document_chunk_index UNIQUE (document_id, chunk_index)
);

-- ==========================================
-- Indexes
-- ==========================================

-- Fast lookup by document (get all chunks for a document)
CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id
ON document_embeddings(document_id);

-- Fast lookup by chunk index (for ordered retrieval)
CREATE INDEX IF NOT EXISTS idx_document_embeddings_chunk_index
ON document_embeddings(chunk_index);

-- JSONB metadata queries (e.g., filter by section_title)
CREATE INDEX IF NOT EXISTS idx_document_embeddings_metadata_gin
ON document_embeddings USING GIN(metadata);

-- IVFFlat index for vector similarity search (cosine distance)
-- Lists parameter: sqrt(total_rows) is a good starting point
-- For 10,000 embeddings, lists=100 is reasonable
-- This index enables fast similarity search using <=> operator
CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding_ivfflat
ON document_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Note: After inserting embeddings, run ANALYZE to optimize query planning
-- ANALYZE document_embeddings;

-- ==========================================
-- Comments
-- ==========================================

COMMENT ON TABLE document_embeddings IS 'Vector embeddings for document chunks (RAG support)';
COMMENT ON COLUMN document_embeddings.id IS 'UUID primary key';
COMMENT ON COLUMN document_embeddings.document_id IS 'Document reference (foreign key)';
COMMENT ON COLUMN document_embeddings.chunk_text IS 'Text chunk that was embedded';
COMMENT ON COLUMN document_embeddings.chunk_index IS 'Order of chunk within document (0-based)';
COMMENT ON COLUMN document_embeddings.embedding IS 'Vector embedding (1536 dimensions, OpenAI)';
COMMENT ON COLUMN document_embeddings.metadata IS 'JSONB metadata: chunk_size, section_title, token_count';
COMMENT ON COLUMN document_embeddings.created_at IS 'Creation timestamp (UTC)';

-- ==========================================
-- Verification
-- ==========================================

DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'document_embeddings') THEN
        RAISE NOTICE 'SUCCESS: document_embeddings table created';
    ELSE
        RAISE EXCEPTION 'FATAL: document_embeddings table creation failed';
    END IF;

    -- Check if indexes exist
    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_embeddings_document_id') THEN
        RAISE NOTICE 'SUCCESS: idx_document_embeddings_document_id created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_embeddings_chunk_index') THEN
        RAISE NOTICE 'SUCCESS: idx_document_embeddings_chunk_index created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_embeddings_metadata_gin') THEN
        RAISE NOTICE 'SUCCESS: idx_document_embeddings_metadata_gin (GIN) created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_embeddings_embedding_ivfflat') THEN
        RAISE NOTICE 'SUCCESS: idx_document_embeddings_embedding_ivfflat (IVFFlat) created';
    END IF;

    -- Check foreign key
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'document_embeddings_document_id%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to documents table created';
    END IF;

    -- Check unique constraint
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_document_chunk_index'
        AND constraint_type = 'UNIQUE'
    ) THEN
        RAISE NOTICE 'SUCCESS: Unique constraint (document_id, chunk_index) created';
    END IF;

    -- Check vector type is available
    IF EXISTS (
        SELECT FROM pg_type
        WHERE typname = 'vector'
    ) THEN
        RAISE NOTICE 'SUCCESS: pgvector type available';
    ELSE
        RAISE EXCEPTION 'FATAL: pgvector extension not installed';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 005: Document Embeddings table complete';
    RAISE NOTICE 'Indexes: 4 created (document_id, chunk_index, metadata GIN, embedding IVFFlat)';
    RAISE NOTICE 'Foreign key: 1 (documents)';
    RAISE NOTICE 'Vector dimension: 1536 (OpenAI text-embedding-3-small)';
    RAISE NOTICE 'Similarity search: Use <=> operator for cosine distance';
    RAISE NOTICE '========================================';
END $$;
