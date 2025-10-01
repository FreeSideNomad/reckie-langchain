-- ==========================================
-- Migration: 001_create_users_table
-- User Story: US-F1-E2-S1
-- Description: Create users table for authentication and authorization
-- ==========================================

-- ==========================================
-- Users Table
-- ==========================================
-- Purpose: Store user accounts for authentication and authorization
-- Used by: All other tables reference this for user tracking
-- ==========================================

CREATE TABLE IF NOT EXISTS users (
    -- Primary identifier using UUID v4
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Unique username for login (3-50 characters)
    username VARCHAR(50) UNIQUE NOT NULL,

    -- User email address for notifications and password reset
    email VARCHAR(255) UNIQUE NOT NULL,

    -- bcrypt or argon2 hashed password (never store plaintext!)
    -- Will be implemented in authentication feature
    password_hash VARCHAR(255) NOT NULL,

    -- User role for authorization: 'user', 'admin', 'qa_lead', 'ddd_designer'
    role VARCHAR(50) NOT NULL DEFAULT 'user',

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- Indexes
-- ==========================================

-- Fast username lookup for login
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Fast email lookup for password reset and notifications
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ==========================================
-- Comments (PostgreSQL table comments)
-- ==========================================

COMMENT ON TABLE users IS 'User accounts with authentication credentials and roles';
COMMENT ON COLUMN users.id IS 'UUID primary key generated on insert';
COMMENT ON COLUMN users.username IS 'Unique username for login (3-50 chars)';
COMMENT ON COLUMN users.email IS 'User email for notifications and recovery';
COMMENT ON COLUMN users.password_hash IS 'bcrypt/argon2 hashed password (never plaintext)';
COMMENT ON COLUMN users.role IS 'User role: user, admin, qa_lead, ddd_designer';
COMMENT ON COLUMN users.created_at IS 'Account creation timestamp (UTC)';
COMMENT ON COLUMN users.updated_at IS 'Last update timestamp (UTC, auto-updated by trigger)';

-- ==========================================
-- Trigger for auto-updating updated_at
-- ==========================================

-- Create trigger function if it doesn't exist (will be used by multiple tables)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to users table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Verification
-- ==========================================

DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'users') THEN
        RAISE NOTICE 'SUCCESS: users table created';
    ELSE
        RAISE EXCEPTION 'FATAL: users table creation failed';
    END IF;

    -- Check if indexes exist
    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_users_username') THEN
        RAISE NOTICE 'SUCCESS: idx_users_username created';
    END IF;

    IF EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_users_email') THEN
        RAISE NOTICE 'SUCCESS: idx_users_email created';
    END IF;

    -- Check if trigger exists
    IF EXISTS (
        SELECT FROM pg_trigger
        WHERE tgname = 'update_users_updated_at'
    ) THEN
        RAISE NOTICE 'SUCCESS: update_users_updated_at trigger created';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 001: Users table complete';
    RAISE NOTICE '========================================';
END $$;
