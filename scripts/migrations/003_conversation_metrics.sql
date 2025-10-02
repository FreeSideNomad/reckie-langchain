-- Migration: Create conversation_metrics table for token tracking
-- Purpose: Track token usage and costs per conversation turn
-- Architecture: Records facts (model, tokens) without hardcoded cost calculations

CREATE TABLE IF NOT EXISTS conversation_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    model VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Metadata for analytics
    correlation_id UUID,
    duration_ms INTEGER,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT
);

-- Index for querying by conversation
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_conversation_id
ON conversation_metrics(conversation_id);

-- Index for time-based queries (cost analytics)
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_created_at
ON conversation_metrics(created_at);

-- Index for model-based analytics
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_model
ON conversation_metrics(model);

COMMENT ON TABLE conversation_metrics IS 'Token usage tracking per conversation turn. Records facts (model + tokens) for cost calculation in analytics layer.';
COMMENT ON COLUMN conversation_metrics.correlation_id IS 'UUID for tracing requests across logs';
COMMENT ON COLUMN conversation_metrics.duration_ms IS 'API call duration in milliseconds';
