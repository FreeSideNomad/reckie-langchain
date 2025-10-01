-- ==========================================
-- Migration: 004_create_document_relationships_table
-- User Story: US-F1-E2-S4
-- Description: Create document_relationships table for hierarchical document relationships
-- Dependencies: documents table (003)
-- ==========================================

-- ==========================================
-- Document Relationships Table
-- ==========================================
-- Purpose: Track parent-child relationships between documents
-- Examples: Vision → Feature, Feature → Epic, Epic → User Story
-- Supports: Hierarchy traversal, breadcrumb generation, ripple effects
-- ==========================================

CREATE TABLE IF NOT EXISTS document_relationships (
    -- Primary identifier using UUID v4
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Parent document (references documents table)
    parent_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Child document (references documents table)
    child_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Relationship type
    -- Values: 'parent_child', 'reference', 'derived_from'
    -- parent_child: Standard hierarchy (Vision → Feature)
    -- reference: Soft reference (Test Plan references Feature)
    -- derived_from: AI-derived relationship
    relationship_type VARCHAR(50) NOT NULL DEFAULT 'parent_child',

    -- Audit timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    -- Prevent duplicate relationships
    CONSTRAINT uq_parent_child UNIQUE (parent_id, child_id),

    -- Prevent self-referencing (document cannot be its own parent)
    CONSTRAINT chk_no_self_reference CHECK (parent_id != child_id)
);

-- ==========================================
-- Indexes
-- ==========================================

-- Fast lookup by parent (get all children of a document)
CREATE INDEX IF NOT EXISTS idx_document_relationships_parent_id
ON document_relationships(parent_id);

-- Fast lookup by child (get all parents of a document)
CREATE INDEX IF NOT EXISTS idx_document_relationships_child_id
ON document_relationships(child_id);

-- Fast filtering by relationship type
CREATE INDEX IF NOT EXISTS idx_document_relationships_type
ON document_relationships(relationship_type);

-- Composite index for ancestor/descendant queries
CREATE INDEX IF NOT EXISTS idx_document_relationships_parent_child
ON document_relationships(parent_id, child_id);

-- ==========================================
-- Comments
-- ==========================================

COMMENT ON TABLE document_relationships IS 'Hierarchical relationships between documents (Vision → Feature → Epic → User Story)';
COMMENT ON COLUMN document_relationships.id IS 'UUID primary key';
COMMENT ON COLUMN document_relationships.parent_id IS 'Parent document (foreign key to documents)';
COMMENT ON COLUMN document_relationships.child_id IS 'Child document (foreign key to documents)';
COMMENT ON COLUMN document_relationships.relationship_type IS 'Type: parent_child, reference, derived_from';
COMMENT ON COLUMN document_relationships.created_at IS 'Creation timestamp (UTC)';

-- ==========================================
-- Verification
-- ==========================================

DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'document_relationships') THEN
        RAISE NOTICE 'SUCCESS: document_relationships table created';
    ELSE
        RAISE EXCEPTION 'FATAL: document_relationships table creation failed';
    END IF;

    -- Check if indexes exist
    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_relationships_parent_id') THEN
        RAISE NOTICE 'SUCCESS: idx_document_relationships_parent_id created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_relationships_child_id') THEN
        RAISE NOTICE 'SUCCESS: idx_document_relationships_child_id created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_relationships_type') THEN
        RAISE NOTICE 'SUCCESS: idx_document_relationships_type created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_relationships_parent_child') THEN
        RAISE NOTICE 'SUCCESS: idx_document_relationships_parent_child (composite) created';
    END IF;

    -- Check foreign keys
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'document_relationships_parent_id%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to documents (parent_id) created';
    END IF;

    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'document_relationships_child_id%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to documents (child_id) created';
    END IF;

    -- Check unique constraint
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_parent_child'
        AND constraint_type = 'UNIQUE'
    ) THEN
        RAISE NOTICE 'SUCCESS: Unique constraint (parent_id, child_id) created';
    END IF;

    -- Check self-reference check constraint
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name = 'chk_no_self_reference'
        AND constraint_type = 'CHECK'
    ) THEN
        RAISE NOTICE 'SUCCESS: Check constraint (no self-reference) created';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 004: Document Relationships table complete';
    RAISE NOTICE 'Indexes: 4 created (parent_id, child_id, type, composite)';
    RAISE NOTICE 'Foreign keys: 2 (documents parent, documents child)';
    RAISE NOTICE 'Constraints: 2 (unique, no self-reference)';
    RAISE NOTICE 'Relationship types: parent_child, reference, derived_from';
    RAISE NOTICE '========================================';
END $$;
