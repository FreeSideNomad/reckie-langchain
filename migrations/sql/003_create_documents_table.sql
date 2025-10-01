-- ==========================================
-- Migration: 003_create_documents_table
-- User Story: US-F1-E2-S3
-- Description: Create documents table for storing all document types
-- Dependencies: users table (001), document_types table (002)
-- ==========================================

-- ==========================================
-- Documents Table
-- ==========================================
-- Purpose: Store all documents (vision, features, epics, user stories, etc.)
-- Central table: Referenced by relationships, embeddings, conversations, versions
-- ==========================================

CREATE TABLE IF NOT EXISTS documents (
    -- Primary identifier using UUID v4
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Document owner (who created/owns this document)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Document type (vision_document, feature_document, user_story, etc.)
    -- References type configuration from document_types table
    document_type VARCHAR(100) NOT NULL REFERENCES document_types(type_name),

    -- Document title (user-friendly display name)
    title VARCHAR(500) NOT NULL,

    -- Rendered markdown content (final output)
    -- Generated from AI conversations
    content_markdown TEXT,

    -- YAML domain model stored as JSON
    -- Contains structured data: objectives, features, acceptance_criteria, etc.
    domain_model JSONB DEFAULT '{}',

    -- Additional metadata as JSONB
    -- Format: {tags: [], priority: "P0", story_points: 3, sprint: "Sprint 1", etc.}
    metadata JSONB DEFAULT '{}',

    -- Document version number (incremented on major changes)
    version INTEGER DEFAULT 1,

    -- Document lifecycle status
    -- Values: 'draft', 'in_progress', 'complete', 'stale'
    status VARCHAR(50) DEFAULT 'draft',

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Audit user references
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- ==========================================
-- Indexes
-- ==========================================

-- Fast lookup by document owner
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);

-- Fast filtering by document type
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);

-- Fast filtering by status (draft, in_progress, complete, stale)
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- Recent documents query (descending order)
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- Recently updated documents (descending order)
CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents(updated_at DESC);

-- JSONB metadata queries (tags, priority, etc.)
CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin ON documents USING GIN(metadata);

-- ==========================================
-- Comments
-- ==========================================

COMMENT ON TABLE documents IS 'All document types: vision, features, epics, user stories, DDD designs, test plans';
COMMENT ON COLUMN documents.id IS 'UUID primary key generated on insert';
COMMENT ON COLUMN documents.user_id IS 'Document owner (foreign key to users)';
COMMENT ON COLUMN documents.document_type IS 'Type: vision_document, feature_document, user_story, etc.';
COMMENT ON COLUMN documents.title IS 'User-friendly document title';
COMMENT ON COLUMN documents.content_markdown IS 'Rendered markdown content (AI-generated)';
COMMENT ON COLUMN documents.domain_model IS 'YAML domain model as JSONB (structured data)';
COMMENT ON COLUMN documents.metadata IS 'JSONB metadata: tags, priority, story_points, sprint, etc.';
COMMENT ON COLUMN documents.version IS 'Version number (incremented on changes)';
COMMENT ON COLUMN documents.status IS 'Lifecycle: draft, in_progress, complete, stale';
COMMENT ON COLUMN documents.created_at IS 'Creation timestamp (UTC)';
COMMENT ON COLUMN documents.updated_at IS 'Last update timestamp (UTC, auto-updated by trigger)';
COMMENT ON COLUMN documents.created_by IS 'User who created document';
COMMENT ON COLUMN documents.updated_by IS 'User who last updated document';

-- ==========================================
-- Apply trigger for updated_at
-- ==========================================

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Verification
-- ==========================================

DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'documents') THEN
        RAISE NOTICE 'SUCCESS: documents table created';
    ELSE
        RAISE EXCEPTION 'FATAL: documents table creation failed';
    END IF;

    -- Check if indexes exist
    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_documents_user_id') THEN
        RAISE NOTICE 'SUCCESS: idx_documents_user_id created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_documents_document_type') THEN
        RAISE NOTICE 'SUCCESS: idx_documents_document_type created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_documents_status') THEN
        RAISE NOTICE 'SUCCESS: idx_documents_status created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_documents_created_at') THEN
        RAISE NOTICE 'SUCCESS: idx_documents_created_at created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_documents_updated_at') THEN
        RAISE NOTICE 'SUCCESS: idx_documents_updated_at created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_documents_metadata_gin') THEN
        RAISE NOTICE 'SUCCESS: idx_documents_metadata_gin (GIN) created';
    END IF;

    -- Check if trigger exists
    IF EXISTS (
        SELECT FROM pg_trigger
        WHERE tgname = 'update_documents_updated_at'
    ) THEN
        RAISE NOTICE 'SUCCESS: update_documents_updated_at trigger created';
    END IF;

    -- Check foreign keys
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'documents_user_id%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to users table created';
    END IF;

    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'documents_document_type%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to document_types table created';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 003: Documents table complete';
    RAISE NOTICE 'Indexes: 6 created (user_id, document_type, status, created_at, updated_at, metadata GIN)';
    RAISE NOTICE 'Foreign keys: 2 (users, document_types)';
    RAISE NOTICE 'Status values: draft, in_progress, complete, stale';
    RAISE NOTICE '========================================';
END $$;
