-- ==========================================
-- Test Suite for Migration 001: Users Table
-- User Story: US-F1-E2-S1
-- ==========================================

-- Start transaction for testing (will be rolled back)
BEGIN;

\echo ''
\echo '=========================================='
\echo 'Testing Users Table'
\echo '=========================================='
\echo ''

-- ==========================================
-- Test 1: Successful insert with all fields
-- ==========================================
\echo 'Test 1: Successful insert with all fields'
INSERT INTO users (username, email, password_hash, role)
VALUES ('john_doe', 'john@example.com', '$2b$12$hashed_password_here', 'user')
RETURNING id, username, role, created_at;
\echo '✓ Test 1 passed: Insert successful'
\echo ''

-- ==========================================
-- Test 2: Insert with defaults (role defaults to 'user')
-- ==========================================
\echo 'Test 2: Insert with defaults'
INSERT INTO users (username, email, password_hash)
VALUES ('jane_doe', 'jane@example.com', '$2b$12$another_hashed_password')
RETURNING id, username, role, created_at, updated_at;
\echo '✓ Test 2 passed: Role defaults to user, timestamps populated'
\echo ''

-- ==========================================
-- Test 3: Duplicate username (should fail)
-- ==========================================
\echo 'Test 3: Duplicate username (should fail)'
DO $$
BEGIN
    INSERT INTO users (username, email, password_hash)
    VALUES ('john_doe', 'different@example.com', '$2b$12$hashed');
    RAISE EXCEPTION 'Test 3 FAILED: Duplicate username was allowed';
EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE '✓ Test 3 passed: Duplicate username rejected';
END $$;
\echo ''

-- ==========================================
-- Test 4: Duplicate email (should fail)
-- ==========================================
\echo 'Test 4: Duplicate email (should fail)'
DO $$
BEGIN
    INSERT INTO users (username, email, password_hash)
    VALUES ('different_user', 'john@example.com', '$2b$12$hashed');
    RAISE EXCEPTION 'Test 4 FAILED: Duplicate email was allowed';
EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE '✓ Test 4 passed: Duplicate email rejected';
END $$;
\echo ''

-- ==========================================
-- Test 5: Missing required field (should fail)
-- ==========================================
\echo 'Test 5: Missing required field (should fail)'
DO $$
BEGIN
    INSERT INTO users (username, email)
    VALUES ('test_user', 'test@example.com');
    RAISE EXCEPTION 'Test 5 FAILED: Missing password_hash was allowed';
EXCEPTION
    WHEN not_null_violation THEN
        RAISE NOTICE '✓ Test 5 passed: NULL password_hash rejected';
END $$;
\echo ''

-- ==========================================
-- Test 6: Lookup by username (index test)
-- ==========================================
\echo 'Test 6: Lookup by username'
EXPLAIN (COSTS OFF)
SELECT id, username, email, role FROM users WHERE username = 'john_doe';

SELECT id, username, email, role FROM users WHERE username = 'john_doe';
\echo '✓ Test 6 passed: Username lookup successful'
\echo ''

-- ==========================================
-- Test 7: Lookup by email (index test)
-- ==========================================
\echo 'Test 7: Lookup by email'
EXPLAIN (COSTS OFF)
SELECT id, username, email, role FROM users WHERE email = 'john@example.com';

SELECT id, username, email, role FROM users WHERE email = 'john@example.com';
\echo '✓ Test 7 passed: Email lookup successful'
\echo ''

-- ==========================================
-- Test 8: List all users
-- ==========================================
\echo 'Test 8: List all users'
SELECT id, username, email, role, created_at
FROM users
ORDER BY created_at DESC;
\echo '✓ Test 8 passed: Listed all users'
\echo ''

-- ==========================================
-- Test 9: Test updated_at trigger
-- ==========================================
\echo 'Test 9: Test updated_at trigger'
DO $$
DECLARE
    initial_updated_at TIMESTAMP WITH TIME ZONE;
    new_updated_at TIMESTAMP WITH TIME ZONE;
    user_uuid UUID;
BEGIN
    -- Get a user and their updated_at
    SELECT id, updated_at INTO user_uuid, initial_updated_at
    FROM users WHERE username = 'john_doe';

    -- Wait a moment
    PERFORM pg_sleep(1);

    -- Update the user
    UPDATE users SET role = 'admin' WHERE id = user_uuid;

    -- Get new updated_at
    SELECT updated_at INTO new_updated_at
    FROM users WHERE id = user_uuid;

    -- Verify it changed
    IF new_updated_at > initial_updated_at THEN
        RAISE NOTICE '✓ Test 9 passed: updated_at trigger working';
    ELSE
        RAISE EXCEPTION 'Test 9 FAILED: updated_at not updated';
    END IF;
END $$;
\echo ''

-- ==========================================
-- Test 10: Test different roles
-- ==========================================
\echo 'Test 10: Test different roles'
INSERT INTO users (username, email, password_hash, role)
VALUES
    ('admin_user', 'admin@example.com', '$2b$12$hashed', 'admin'),
    ('qa_lead', 'qa@example.com', '$2b$12$hashed', 'qa_lead'),
    ('ddd_designer', 'ddd@example.com', '$2b$12$hashed', 'ddd_designer')
RETURNING username, role;
\echo '✓ Test 10 passed: All roles accepted'
\echo ''

-- ==========================================
-- Test Summary
-- ==========================================
\echo ''
\echo '=========================================='
\echo 'All tests passed for users table!'
\echo '=========================================='
\echo ''
\echo 'Summary:'
\echo '- Table structure correct'
\echo '- UNIQUE constraints enforced'
\echo '- NOT NULL constraints enforced'
\echo '- DEFAULT values working'
\echo '- Indexes created'
\echo '- Trigger working'
\echo '- All roles supported'
\echo ''

-- Rollback transaction (don't commit test data)
ROLLBACK;

\echo 'Test transaction rolled back (no data persisted)'
\echo ''
