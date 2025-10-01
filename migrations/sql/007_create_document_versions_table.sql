-- ==========================================
-- Migration: 007_create_document_versions_table
-- User Story: US-F1-E2-S7
-- Description: Create document_versions table for version history and audit trail
-- Dependencies: documents table (003), users table (001)
-- ==========================================

-- ==========================================
-- Document Versions Table
-- ==========================================
-- Purpose: Track complete version history of document changes
-- Enables: Rollback to previous versions, audit trail, change tracking
-- Stores: Complete snapshot of document at each version
-- ==========================================

CREATE TABLE IF NOT EXISTS document_versions (
    -- Primary identifier using UUID v4
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Document reference (foreign key to documents)
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Version number (incremental: 1, 2, 3, ...)
    version INTEGER NOT NULL,

    -- Snapshot of content at this version
    content_markdown TEXT,

    -- Snapshot of domain model at this version
    domain_model JSONB DEFAULT '{}',

    -- User who made this change
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- When this version was created
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Optional description of what changed
    change_description TEXT,

    -- Constraints
    -- Prevent duplicate version numbers for same document
    CONSTRAINT uq_document_version UNIQUE (document_id, version),

    -- Ensure version number is positive
    CONSTRAINT chk_version_positive CHECK (version > 0)
);

-- ==========================================
-- Indexes
-- ==========================================

-- Fast lookup by document (get all versions of a document)
CREATE INDEX IF NOT EXISTS idx_document_versions_document_id
ON document_versions(document_id);

-- Fast lookup by version number
CREATE INDEX IF NOT EXISTS idx_document_versions_version
ON document_versions(version);

-- Composite index for document + version queries
CREATE INDEX IF NOT EXISTS idx_document_versions_document_version
ON document_versions(document_id, version DESC);

-- Fast filtering by change date (recent changes)
CREATE INDEX IF NOT EXISTS idx_document_versions_changed_at
ON document_versions(changed_at DESC);

-- Fast lookup by user (see all changes by a user)
CREATE INDEX IF NOT EXISTS idx_document_versions_changed_by
ON document_versions(changed_by);

-- JSONB domain model queries
CREATE INDEX IF NOT EXISTS idx_document_versions_domain_model_gin
ON document_versions USING GIN(domain_model);

-- ==========================================
-- Comments
-- ==========================================

COMMENT ON TABLE document_versions IS 'Complete version history of document changes (audit trail, rollback support)';
COMMENT ON COLUMN document_versions.id IS 'UUID primary key';
COMMENT ON COLUMN document_versions.document_id IS 'Document reference (foreign key to documents)';
COMMENT ON COLUMN document_versions.version IS 'Version number (incremental: 1, 2, 3, ...)';
COMMENT ON COLUMN document_versions.content_markdown IS 'Snapshot of content at this version';
COMMENT ON COLUMN document_versions.domain_model IS 'Snapshot of domain model at this version (JSONB)';
COMMENT ON COLUMN document_versions.changed_by IS 'User who made this change (foreign key to users)';
COMMENT ON COLUMN document_versions.changed_at IS 'Timestamp when version was created (UTC)';
COMMENT ON COLUMN document_versions.change_description IS 'Optional description of changes in this version';

-- ==========================================
-- Verification
-- ==========================================

DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'document_versions') THEN
        RAISE NOTICE 'SUCCESS: document_versions table created';
    ELSE
        RAISE EXCEPTION 'FATAL: document_versions table creation failed';
    END IF;

    -- Check if indexes exist
    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_versions_document_id') THEN
        RAISE NOTICE 'SUCCESS: idx_document_versions_document_id created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_versions_version') THEN
        RAISE NOTICE 'SUCCESS: idx_document_versions_version created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_versions_document_version') THEN
        RAISE NOTICE 'SUCCESS: idx_document_versions_document_version (composite) created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_versions_changed_at') THEN
        RAISE NOTICE 'SUCCESS: idx_document_versions_changed_at created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_versions_changed_by') THEN
        RAISE NOTICE 'SUCCESS: idx_document_versions_changed_by created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_versions_domain_model_gin') THEN
        RAISE NOTICE 'SUCCESS: idx_document_versions_domain_model_gin (GIN) created';
    END IF;

    -- Check foreign keys
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'document_versions_document_id%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to documents table created';
    END IF;

    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'document_versions_changed_by%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to users table created';
    END IF;

    -- Check unique constraint
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_document_version'
        AND constraint_type = 'UNIQUE'
    ) THEN
        RAISE NOTICE 'SUCCESS: Unique constraint (document_id, version) created';
    END IF;

    -- Check positive version constraint
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name = 'chk_version_positive'
        AND constraint_type = 'CHECK'
    ) THEN
        RAISE NOTICE 'SUCCESS: Check constraint (version > 0) created';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 007: Document Versions table complete';
    RAISE NOTICE 'Indexes: 6 created (document_id, version, composite, changed_at, changed_by, domain_model GIN)';
    RAISE NOTICE 'Foreign keys: 2 (documents, users with ON DELETE SET NULL)';
    RAISE NOTICE 'Constraints: 2 (unique version per document, positive version number)';
    RAISE NOTICE 'Use case: Version history, rollback, audit trail';
    RAISE NOTICE '========================================';
END $$;
