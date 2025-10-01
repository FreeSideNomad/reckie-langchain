-- ==========================================
-- Migration: 006_create_conversations_table
-- User Story: US-F1-E2-S6
-- Description: Create conversations table for AI conversation history
-- Dependencies: users table (001), documents table (003)
-- ==========================================

-- ==========================================
-- Conversations Table
-- ==========================================
-- Purpose: Store conversation history between users and AI for each document
-- Enables: Multi-turn context-aware conversations, conversation resume
-- Used by: LangChain PostgresChatMessageHistory integration
-- ==========================================

CREATE TABLE IF NOT EXISTS conversations (
    -- Primary identifier using UUID v4
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User who owns this conversation
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Document being discussed
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Conversation history as JSONB array
    -- Format: [
    --   {role: "user", content: "Create a vision document", timestamp: "2025-10-01T12:00:00Z"},
    --   {role: "assistant", content: "I'll help you...", timestamp: "2025-10-01T12:00:05Z"}
    -- ]
    history JSONB DEFAULT '[]',

    -- Conversation state as JSONB
    -- Format: {
    --   current_step: "define_vision",
    --   turn_count: 5,
    --   started_at: "2025-10-01T12:00:00Z",
    --   last_activity_at: "2025-10-01T12:15:00Z",
    --   workflow_data: {}
    -- }
    state JSONB DEFAULT '{}',

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    -- One conversation per user per document
    CONSTRAINT uq_user_document UNIQUE (user_id, document_id)
);

-- ==========================================
-- Indexes
-- ==========================================

-- Fast lookup by user (get all user's conversations)
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Fast lookup by document (get conversation for a document)
CREATE INDEX IF NOT EXISTS idx_conversations_document_id ON conversations(document_id);

-- Fast filtering by recent activity
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);

-- JSONB history queries (search messages)
CREATE INDEX IF NOT EXISTS idx_conversations_history_gin ON conversations USING GIN(history);

-- JSONB state queries (filter by workflow step)
CREATE INDEX IF NOT EXISTS idx_conversations_state_gin ON conversations USING GIN(state);

-- ==========================================
-- Comments
-- ==========================================

COMMENT ON TABLE conversations IS 'AI conversation history for document creation workflows';
COMMENT ON COLUMN conversations.id IS 'UUID primary key';
COMMENT ON COLUMN conversations.user_id IS 'User who owns conversation (foreign key to users)';
COMMENT ON COLUMN conversations.document_id IS 'Document being discussed (foreign key to documents)';
COMMENT ON COLUMN conversations.history IS 'JSONB array of messages: [{role, content, timestamp}]';
COMMENT ON COLUMN conversations.state IS 'JSONB workflow state: {current_step, turn_count, started_at, workflow_data}';
COMMENT ON COLUMN conversations.created_at IS 'Creation timestamp (UTC)';
COMMENT ON COLUMN conversations.updated_at IS 'Last update timestamp (UTC, auto-updated by trigger)';

-- ==========================================
-- Apply trigger for updated_at
-- ==========================================

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Verification
-- ==========================================

DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'conversations') THEN
        RAISE NOTICE 'SUCCESS: conversations table created';
    ELSE
        RAISE EXCEPTION 'FATAL: conversations table creation failed';
    END IF;

    -- Check if indexes exist
    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_conversations_user_id') THEN
        RAISE NOTICE 'SUCCESS: idx_conversations_user_id created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_conversations_document_id') THEN
        RAISE NOTICE 'SUCCESS: idx_conversations_document_id created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_conversations_updated_at') THEN
        RAISE NOTICE 'SUCCESS: idx_conversations_updated_at created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_conversations_history_gin') THEN
        RAISE NOTICE 'SUCCESS: idx_conversations_history_gin (GIN) created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_conversations_state_gin') THEN
        RAISE NOTICE 'SUCCESS: idx_conversations_state_gin (GIN) created';
    END IF;

    -- Check if trigger exists
    IF EXISTS (
        SELECT FROM pg_trigger
        WHERE tgname = 'update_conversations_updated_at'
    ) THEN
        RAISE NOTICE 'SUCCESS: update_conversations_updated_at trigger created';
    END IF;

    -- Check foreign keys
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'conversations_user_id%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to users table created';
    END IF;

    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'conversations_document_id%'
        AND constraint_type = 'FOREIGN KEY'
    ) THEN
        RAISE NOTICE 'SUCCESS: Foreign key to documents table created';
    END IF;

    -- Check unique constraint
    IF EXISTS (
        SELECT FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_user_document'
        AND constraint_type = 'UNIQUE'
    ) THEN
        RAISE NOTICE 'SUCCESS: Unique constraint (user_id, document_id) created';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 006: Conversations table complete';
    RAISE NOTICE 'Indexes: 5 created (user_id, document_id, updated_at, history GIN, state GIN)';
    RAISE NOTICE 'Foreign keys: 2 (users, documents)';
    RAISE NOTICE 'Constraint: 1 (one conversation per user per document)';
    RAISE NOTICE 'Trigger: updated_at auto-update';
    RAISE NOTICE '========================================';
END $$;
