-- ==========================================
-- PostgreSQL Initialization Script
-- ==========================================
-- Purpose: Install required extensions and configure database
-- Executed: Automatically by Docker on first container start
-- Location: Mounted to /docker-entrypoint-initdb.d/init.sql
-- ==========================================

-- Set timezone to UTC
SET timezone = 'UTC';

-- Create pgvector extension for vector embeddings
-- Required for: Storing OpenAI embeddings (1536 dimensions)
-- Used by: document_embeddings table
CREATE EXTENSION IF NOT EXISTS vector;

-- Create uuid-ossp extension for UUID generation
-- Required for: Primary keys in tables (uuid_generate_v4())
-- Used by: All tables with UUID primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================
-- Verification
-- ==========================================

-- Verify pgvector extension installed successfully
DO $$
DECLARE
    ext_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO ext_count
    FROM pg_extension
    WHERE extname = 'vector';

    IF ext_count = 0 THEN
        RAISE EXCEPTION 'FATAL: pgvector extension failed to install. Check PostgreSQL version and image.';
    ELSE
        RAISE NOTICE 'SUCCESS: pgvector extension installed (version: %)',
            (SELECT extversion FROM pg_extension WHERE extname = 'vector');
    END IF;
END $$;

-- Verify uuid-ossp extension installed
DO $$
DECLARE
    ext_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO ext_count
    FROM pg_extension
    WHERE extname = 'uuid-ossp';

    IF ext_count = 0 THEN
        RAISE EXCEPTION 'FATAL: uuid-ossp extension failed to install.';
    ELSE
        RAISE NOTICE 'SUCCESS: uuid-ossp extension installed';
    END IF;
END $$;

-- Test vector functionality
DO $$
DECLARE
    test_vector vector(3);
BEGIN
    -- Create a test vector to verify pgvector works
    test_vector := '[1,2,3]'::vector;
    RAISE NOTICE 'SUCCESS: Vector operations functional (test vector: %)', test_vector;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'FATAL: Vector operations failed: %', SQLERRM;
END $$;

-- ==========================================
-- Database Configuration
-- ==========================================

-- Set statement timeout (optional, for safety)
-- ALTER DATABASE langchain_docs SET statement_timeout = '60s';

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Database initialization complete';
    RAISE NOTICE 'Timezone: UTC';
    RAISE NOTICE 'Extensions: vector, uuid-ossp';
    RAISE NOTICE '========================================';
END $$;
