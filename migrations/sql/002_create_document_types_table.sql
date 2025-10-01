-- ==========================================
-- Migration: 002_create_document_types_table
-- User Story: US-F1-E2-S2
-- Description: Create document_types table for configuration of all 9 document types
-- ==========================================

-- ==========================================
-- Document Types Table
-- ==========================================
-- Purpose: Configure all 9 document types with prompts and workflows
-- Used by: Documents table references this for type validation
-- ==========================================

CREATE TABLE IF NOT EXISTS document_types (
    -- Auto-incrementing primary key
    id SERIAL PRIMARY KEY,

    -- Document type name (e.g., 'vision_document', 'user_story')
    -- Must match application code expectations
    type_name VARCHAR(100) UNIQUE NOT NULL,

    -- System prompt for AI conversations
    -- Loaded from config/document_prompts.yaml
    system_prompt TEXT NOT NULL,

    -- Workflow steps as JSONB array
    -- Format: [{step_id, question_count, validation_rules}, ...]
    workflow_steps JSONB NOT NULL DEFAULT '[]',

    -- Allowed parent document types (hierarchical validation)
    -- Format: ["vision_document", "feature_document"]
    parent_types JSONB DEFAULT '[]',

    -- Personas allowed to create this document type
    -- Format: ["business_analyst", "product_owner", "qa_lead", "ddd_designer"]
    allowed_personas JSONB DEFAULT '["business_analyst"]',

    -- Additional configuration (flexible for future needs)
    -- Format: {min_sections, max_sections, required_fields, etc.}
    config JSONB DEFAULT '{}',

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- Indexes
-- ==========================================

-- Fast lookup by type name (primary access pattern)
CREATE INDEX IF NOT EXISTS idx_document_types_type_name ON document_types(type_name);

-- ==========================================
-- Comments
-- ==========================================

COMMENT ON TABLE document_types IS 'Configuration for all 9 document types with AI prompts and workflows';
COMMENT ON COLUMN document_types.id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN document_types.type_name IS 'Unique document type identifier (e.g., vision_document)';
COMMENT ON COLUMN document_types.system_prompt IS 'AI system prompt loaded from YAML config';
COMMENT ON COLUMN document_types.workflow_steps IS 'JSONB array of workflow step configurations';
COMMENT ON COLUMN document_types.parent_types IS 'JSONB array of allowed parent document type names';
COMMENT ON COLUMN document_types.allowed_personas IS 'JSONB array of personas who can create this type';
COMMENT ON COLUMN document_types.config IS 'JSONB object for additional type-specific configuration';

-- ==========================================
-- Apply trigger for updated_at
-- ==========================================

CREATE TRIGGER update_document_types_updated_at
    BEFORE UPDATE ON document_types
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Seed Data: All 9 Document Types
-- ==========================================

-- 1. Research Report
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'research_report',
    'You are a business analyst helping create a research report for Canadian banking systems. Ask 3-5 clarifying questions per turn to build comprehensive research documentation.',
    '[
        {"step_id": "define_research_questions", "question_count": 3},
        {"step_id": "gather_findings", "question_count": 4},
        {"step_id": "analysis", "question_count": 3},
        {"step_id": "recommendations", "question_count": 2}
    ]'::jsonb,
    '[]'::jsonb,
    '["business_analyst"]'::jsonb,
    '{
        "min_sections": 4,
        "required_fields": ["research_questions", "findings", "recommendations"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 2. Business Context
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'business_context',
    'You are a business analyst helping establish business context for the Canadian banking domain. Focus on domain understanding, stakeholders, and business rules.',
    '[
        {"step_id": "define_domain", "question_count": 3},
        {"step_id": "identify_stakeholders", "question_count": 4},
        {"step_id": "business_rules", "question_count": 3}
    ]'::jsonb,
    '[]'::jsonb,
    '["business_analyst", "product_owner"]'::jsonb,
    '{
        "domain": "Canadian Banking",
        "required_fields": ["domain_description", "stakeholders", "business_rules"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 3. Vision Document
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'vision_document',
    'You are a product owner helping create a product vision document. Guide the user through vision statement, objectives, success metrics, and feature derivation.',
    '[
        {"step_id": "vision_statement", "question_count": 3},
        {"step_id": "objectives", "question_count": 4},
        {"step_id": "success_metrics", "question_count": 3},
        {"step_id": "derive_features", "question_count": 5}
    ]'::jsonb,
    '["research_report", "business_context"]'::jsonb,
    '["product_owner"]'::jsonb,
    '{
        "min_features": 10,
        "max_features": 30,
        "required_fields": ["vision_statement", "objectives", "success_metrics", "features"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 4. Feature Document
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'feature_document',
    'You are a product owner elaborating a feature from the vision. Define feature details, business value, acceptance criteria, and derive epics.',
    '[
        {"step_id": "feature_description", "question_count": 3},
        {"step_id": "business_value", "question_count": 3},
        {"step_id": "acceptance_criteria", "question_count": 5},
        {"step_id": "technical_design", "question_count": 4},
        {"step_id": "derive_epics", "question_count": 4}
    ]'::jsonb,
    '["vision_document"]'::jsonb,
    '["product_owner"]'::jsonb,
    '{
        "min_epics": 2,
        "max_epics": 10,
        "required_fields": ["description", "business_value", "epics"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 5. Epic Document
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'epic_document',
    'You are a product owner breaking down an epic into user stories. Define epic scope, acceptance criteria, and derive implementable user stories.',
    '[
        {"step_id": "epic_description", "question_count": 3},
        {"step_id": "acceptance_criteria", "question_count": 4},
        {"step_id": "derive_stories", "question_count": 5}
    ]'::jsonb,
    '["feature_document"]'::jsonb,
    '["product_owner"]'::jsonb,
    '{
        "min_stories": 3,
        "max_stories": 15,
        "required_fields": ["description", "acceptance_criteria", "user_stories"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 6. User Story
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'user_story',
    'You are a product owner creating detailed user story specifications. Use the format: As a [role], I want [capability], So that [benefit]. Include comprehensive acceptance criteria.',
    '[
        {"step_id": "story_statement", "question_count": 2},
        {"step_id": "acceptance_criteria", "question_count": 5},
        {"step_id": "implementation_details", "question_count": 6},
        {"step_id": "testing_checklist", "question_count": 3}
    ]'::jsonb,
    '["epic_document"]'::jsonb,
    '["product_owner"]'::jsonb,
    '{
        "story_point_range": [1, 13],
        "required_fields": ["as_a", "i_want", "so_that", "acceptance_criteria"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 7. DDD Design Document
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'ddd_design',
    'You are a DDD designer creating domain models. Identify bounded contexts, aggregates, entities, value objects, and domain events using Domain-Driven Design principles.',
    '[
        {"step_id": "identify_aggregates", "question_count": 4},
        {"step_id": "define_entities", "question_count": 5},
        {"step_id": "value_objects", "question_count": 4},
        {"step_id": "domain_events", "question_count": 3}
    ]'::jsonb,
    '["feature_document", "epic_document"]'::jsonb,
    '["ddd_designer"]'::jsonb,
    '{
        "required_fields": ["aggregates", "entities", "value_objects", "bounded_context"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 8. Testing Strategy
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'testing_strategy',
    'You are a QA lead defining the overall testing approach. Cover test levels, test types, automation strategy, and quality metrics.',
    '[
        {"step_id": "test_levels", "question_count": 4},
        {"step_id": "test_types", "question_count": 4},
        {"step_id": "automation_strategy", "question_count": 3},
        {"step_id": "quality_metrics", "question_count": 3}
    ]'::jsonb,
    '["vision_document"]'::jsonb,
    '["qa_lead"]'::jsonb,
    '{
        "required_fields": ["test_levels", "test_types", "automation", "metrics"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- 9. Test Plan
INSERT INTO document_types (type_name, system_prompt, workflow_steps, parent_types, allowed_personas, config)
VALUES (
    'test_plan',
    'You are a QA lead creating a feature-specific test plan. Define scope, test cases, test data, and entry/exit criteria.',
    '[
        {"step_id": "test_scope", "question_count": 3},
        {"step_id": "test_cases", "question_count": 6},
        {"step_id": "test_data", "question_count": 3},
        {"step_id": "entry_exit_criteria", "question_count": 2}
    ]'::jsonb,
    '["feature_document", "epic_document"]'::jsonb,
    '["qa_lead"]'::jsonb,
    '{
        "min_test_cases": 5,
        "required_fields": ["scope", "test_cases", "test_data"]
    }'::jsonb
) ON CONFLICT (type_name) DO NOTHING;

-- ==========================================
-- Verification
-- ==========================================

DO $$
DECLARE
    type_count INTEGER;
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'document_types') THEN
        RAISE NOTICE 'SUCCESS: document_types table created';
    ELSE
        RAISE EXCEPTION 'FATAL: document_types table creation failed';
    END IF;

    -- Check if all 9 types were inserted
    SELECT COUNT(*) INTO type_count FROM document_types;
    IF type_count = 9 THEN
        RAISE NOTICE 'SUCCESS: All 9 document types seeded';
    ELSE
        RAISE EXCEPTION 'FATAL: Expected 9 document types, found %', type_count;
    END IF;

    -- Check if index exists
    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_document_types_type_name') THEN
        RAISE NOTICE 'SUCCESS: idx_document_types_type_name created';
    END IF;

    -- Check if trigger exists
    IF EXISTS (
        SELECT FROM pg_trigger
        WHERE tgname = 'update_document_types_updated_at'
    ) THEN
        RAISE NOTICE 'SUCCESS: update_document_types_updated_at trigger created';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 002: Document Types complete';
    RAISE NOTICE 'Document types: research_report, business_context,';
    RAISE NOTICE '                vision_document, feature_document,';
    RAISE NOTICE '                epic_document, user_story,';
    RAISE NOTICE '                ddd_design, testing_strategy, test_plan';
    RAISE NOTICE '========================================';
END $$;
