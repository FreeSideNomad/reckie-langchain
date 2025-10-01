# Claude Code - LLM Agent Development Workflow

This document defines the complete development workflow for this project when working with Claude Code (LLM Agent).

## Core Principles

1. **Issue-Driven Development:** All work tracked in GitHub Issues
2. **Feature Branching:** One branch per user story
3. **Clean Builds Only:** PRs only created after successful CI/CD
4. **Test Coverage:** Minimum 85% line and branch coverage required
5. **LLM Attribution:** All commits include Claude Code attribution

## Complete User Story Workflow

### Phase 1: Verify Issue Exists

**Before starting ANY user story implementation:**

```bash
# Check if issue exists in GitHub
gh issue view <issue-number>

# If issue doesn't exist, create it first
# Use GitHub issue templates: user-story.yml, epic.yml, or feature.yml
```

**Rule:** Never implement a user story without a corresponding GitHub issue.

### Phase 2: Create Feature Branch

**Branch Naming Convention:** `feature/us-<epic-id>-<story-id>-<slug>`

```bash
# Switch to main branch
git checkout main
git pull origin main

# Create feature branch for user story
git checkout -b feature/us-f1-e1-s2-pgvector-extension

# Verify branch
git branch --show-current
```

**Example Branch Names:**
- `feature/us-f1-e1-s1-docker-compose`
- `feature/us-f1-e1-s2-pgvector-extension`
- `feature/us-f1-e1-s3-environment-config`

### Phase 3: Setup Python Virtual Environment (if not already done)

**First time setup:**

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements-dev.txt
```

**For subsequent work (always activate venv first):**

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux

# Verify you're in venv (should show venv path)
which python
```

### Phase 4: Implementation

Implement the user story according to:
- Acceptance criteria from GitHub issue
- Technical details from wiki documentation
- Testing requirements from issue checklist

```bash
# Ensure venv is activated
source venv/bin/activate

# Create/modify files as needed
# Follow project structure and coding standards
```

### Phase 5: Test Locally

```bash
# Ensure venv is activated
source venv/bin/activate

pytest --cov=src --cov-report=term --cov-report=html

# Check coverage meets 85% threshold
# Line coverage: ≥85%
# Branch coverage: ≥85%

# Fix any failing tests or coverage gaps
```

### Phase 6: Commit Changes

**Commit Message Format:**

```
Implement <Issue-ID>: <Title>

<Detailed description of changes>

<List of files created/modified>

<Testing results>

Closes #<issue-number>

🤖 Implemented by: Claude Code (LLM Agent)
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Example:**

```bash
git add .
git commit -m "Implement US-F1-E1-S2: pgvector Extension Installation

Created scripts/init_db.sql with:
- pgvector extension installation
- uuid-ossp extension installation
- Timezone configuration (UTC)
- Extension verification checks
- Test vector operations

Testing completed:
✓ Extensions install successfully
✓ Vector operations functional
✓ UUID generation works
✓ Idempotent (can run multiple times)

Closes #5

🤖 Implemented by: Claude Code (LLM Agent)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Phase 7: Push and Check CI/CD

```bash
# Push feature branch
git push -u origin feature/us-<epic-id>-<story-id>-<slug>

# Wait for GitHub Actions to complete
# Check workflow status
gh run list --branch feature/us-<epic-id>-<story-id>-<slug>

# If workflow fails, check logs
gh run view <run-id> --log-failed
```

### Phase 8: Fix CI/CD Failures

**If GitHub Actions workflow fails:**

```bash
# Review error logs
gh run view --log-failed

# Identify issues:
# - Test failures
# - Coverage below 85%
# - Linting errors
# - Type checking errors

# Fix issues locally
# ... make fixes ...

# Re-test locally
pytest --cov=src --cov-report=term

# Commit fixes
git add .
git commit -m "Fix CI/CD: <description of fixes>

Addresses:
- <issue 1>
- <issue 2>

All tests now passing with 85%+ coverage.

🤖 Fixed by: Claude Code (LLM Agent)
Co-Authored-By: Claude <noreply@anthropic.com>"

# Push again
git push origin feature/us-<epic-id>-<story-id>-<slug>

# Check workflow again
gh run list --branch feature/us-<epic-id>-<story-id>-<slug>
```

**Repeat Phase 8 until workflow succeeds** ✅

### Phase 9: Create Pull Request (Only After Clean Build)

**Rule:** Only create PR when CI/CD is green ✅

```bash
# Verify workflow is successful
gh run list --branch feature/us-<epic-id>-<story-id>-<slug> --limit 1

# Status must be "completed" with conclusion "success"
# ✅ If successful, create PR
# ❌ If failed, return to Phase 7

# Create PR with detailed description
gh pr create \
  --title "[<Issue-ID>] <Title>" \
  --body "<PR description with summary, changes, testing, closes #N>" \
  --base main
```

**PR Description Template:**

```markdown
## Summary

Implements **User Story <ID>**: <Title>

Closes #<issue-number>

## Changes

### Files Created/Modified
- ✅ `file1.py` - Description
- ✅ `file2.py` - Description

## Acceptance Criteria

All acceptance criteria from Issue #<N> have been met:

- [x] AC1: Description
- [x] AC2: Description
- [x] AC3: Description

## Testing Results

### Unit Tests ✅
- [x] All tests passing
- [x] Line coverage: X%
- [x] Branch coverage: Y%

### Manual Testing ✅
- [x] Test case 1
- [x] Test case 2

## CI/CD Status

✅ GitHub Actions workflow successful
- Tests: PASSED
- Coverage: X% (≥85% required)
- Linting: PASSED
- Type Checking: PASSED

## Related Issues

- Part of: **Epic #<N>** (<Epic Name>)
- Part of: **Feature #<N>** (<Feature Name>)
- Blocks: **Issue #<N>** (Next user story)

---

🤖 **Implemented by:** Claude Code (LLM Agent)

**Co-Authored-By:** Claude <noreply@anthropic.com>
```

### Phase 10: Continue to Next User Story

**After PR is created and merged:**

```bash
# Switch back to main
git checkout main
git pull origin main

# Start next user story (return to Phase 1)
```

---

## GitHub Actions CI/CD Requirements

### Workflow Triggers

```yaml
on:
  push:
    branches: ['main', 'feature/**']
  pull_request:
    branches: ['main']
```

### Required Checks

1. **Python Linting** (flake8, black, isort)
2. **Type Checking** (mypy)
3. **Unit Tests** (pytest)
4. **Code Coverage** (pytest-cov)
   - Minimum: 85% line coverage
   - Minimum: 85% branch coverage
5. **Security Scan** (bandit)
6. **Dependency Check** (safety)

### Test Coverage Thresholds

```ini
# pytest.ini or pyproject.toml
[tool:pytest]
addopts = --cov=src --cov-report=term --cov-report=html --cov-fail-under=85
```

**Coverage Requirements:**
- **Line Coverage:** ≥85%
- **Branch Coverage:** ≥85%
- **Missing:** Fail build if below threshold

### Workflow Jobs

```yaml
jobs:
  lint:
    - flake8
    - black --check
    - isort --check

  type-check:
    - mypy src/

  test:
    - pytest --cov=src --cov-fail-under=85

  security:
    - bandit -r src/
    - safety check

  build:
    - python -m build
```

---

## Commit Message Standards

### Format

```
<Type> <Scope>: <Subject>

<Body>

<Footer>
```

### Types

- `Implement` - Implementing a user story
- `Fix` - Bug fix or CI/CD fix
- `Refactor` - Code refactoring
- `Test` - Adding tests
- `Docs` - Documentation changes
- `Chore` - Maintenance tasks

### Examples

**User Story Implementation:**
```
Implement US-F1-E1-S1: Docker Compose File Creation

Created docker-compose.yml with PostgreSQL + pgvector.
All acceptance criteria met.

Closes #3

🤖 Implemented by: Claude Code (LLM Agent)
Co-Authored-By: Claude <noreply@anthropic.com>
```

**CI/CD Fix:**
```
Fix CI/CD: Add missing pytest dependency

GitHub Actions workflow was failing due to missing pytest-cov.
Added to requirements-dev.txt.

All tests now passing with 87% coverage.

🤖 Fixed by: Claude Code (LLM Agent)
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Error Handling Workflow

### When CI/CD Fails

1. **Check Logs:**
   ```bash
   gh run view --log-failed
   ```

2. **Identify Root Cause:**
   - Test failures → Fix tests
   - Coverage below 85% → Add tests
   - Linting errors → Run `black .` and `isort .`
   - Type errors → Fix type hints

3. **Fix Locally:**
   ```bash
   # Run checks locally
   pytest --cov=src --cov-fail-under=85
   black .
   isort .
   mypy src/
   ```

4. **Commit Fix:**
   ```bash
   git add .
   git commit -m "Fix CI/CD: <description>"
   git push origin <branch-name>
   ```

5. **Verify Fix:**
   ```bash
   gh run list --branch <branch-name> --limit 1
   ```

6. **Repeat Until Green:** ✅

---

## Quick Reference Checklist

### Before Starting Work
- [ ] Issue exists in GitHub
- [ ] Switched to main branch
- [ ] Created feature branch with correct naming

### During Implementation
- [ ] Following acceptance criteria from issue
- [ ] Writing unit tests as you go
- [ ] Running local tests frequently

### Before First Push
- [ ] All tests passing locally
- [ ] Coverage ≥85% (line and branch)
- [ ] Code formatted (black, isort)
- [ ] Type hints added (mypy clean)

### After Push
- [ ] Check GitHub Actions workflow status
- [ ] If failed: review logs, fix, commit, push again
- [ ] If successful: proceed to create PR

### Creating PR
- [ ] CI/CD is green ✅
- [ ] PR title follows format: `[Issue-ID] Title`
- [ ] PR body includes: summary, changes, testing, closes #N
- [ ] PR references related issues (epic, feature)
- [ ] LLM attribution included

### After PR Merged
- [ ] Switch to main branch
- [ ] Pull latest changes
- [ ] Start next user story

---

## File Structure

```
langchain-demo/
├── .github/
│   ├── workflows/
│   │   └── ci.yml                 # GitHub Actions workflow
│   └── ISSUE_TEMPLATE/
│       ├── feature.yml
│       ├── epic.yml
│       └── user-story.yml
├── src/                           # Source code
│   └── ...
├── tests/                         # Unit tests
│   └── ...
├── scripts/                       # Utility scripts
│   └── ...
├── wiki/                          # Documentation (git submodule)
│   └── *.md
├── CLAUDE.md                      # This file
├── README.md                      # Project overview
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Development dependencies
├── pytest.ini                     # Pytest configuration
├── .coveragerc                    # Coverage configuration
├── pyproject.toml                 # Project configuration
└── docker-compose.yml             # Local development
```

---

## Best Practices

### DO ✅

- **Always** check if GitHub issue exists before starting
- **Always** create feature branch before implementation
- **Always** run tests locally before pushing
- **Always** check CI/CD logs if workflow fails
- **Always** fix issues until workflow is green
- **Always** include LLM attribution in commits
- **Only** create PR after successful CI/CD run
- **Always** close issue with "Closes #N" in PR

### DON'T ❌

- ❌ Start implementation without GitHub issue
- ❌ Push directly to main branch
- ❌ Create PR with failing CI/CD
- ❌ Skip tests or coverage checks
- ❌ Ignore CI/CD failures
- ❌ Commit without LLM attribution
- ❌ Merge PR without review (for human PRs)
- ❌ Leave broken builds in feature branches

---

## Automation Tools

### GitHub CLI Commands

```bash
# View issue
gh issue view <number>

# Create issue from template
gh issue create --template user-story.yml

# List workflow runs
gh run list --branch <branch-name>

# View workflow logs
gh run view <run-id> --log

# View failed logs only
gh run view <run-id> --log-failed

# Create PR
gh pr create --title "..." --body "..."

# Check PR status
gh pr view <number>

# Merge PR (after review)
gh pr merge <number> --squash
```

### Local Testing Scripts

```bash
# Run all checks locally (create as scripts/check.sh)
#!/bin/bash
set -e

echo "Running linting..."
black --check src/
isort --check src/
flake8 src/

echo "Running type checking..."
mypy src/

echo "Running tests with coverage..."
pytest --cov=src --cov-fail-under=85 --cov-report=term

echo "Running security checks..."
bandit -r src/
safety check

echo "✅ All checks passed!"
```

---

## Summary

**Complete Workflow in One Diagram:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Verify Issue Exists (#N)                                 │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Create Feature Branch (feature/us-X-Y-Z-slug)            │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Implement User Story (following AC from issue)           │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Test Locally (pytest, coverage ≥85%)                     │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Commit (with "Closes #N" and LLM attribution)            │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Push Feature Branch                                      │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Check GitHub Actions (gh run list)                       │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. CI/CD Failed? → Fix → Commit → Push → Check Again        │
│    Repeat until ✅ GREEN                                     │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. ✅ CI/CD Green? → Create PR (gh pr create)               │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. PR Merged → Checkout main → Start Next Story            │
└─────────────────────────────────────────────────────────────┘
```

**Key Rule:** 🚫 **NO PR WITHOUT GREEN CI/CD** ✅

---

**Last Updated:** 2025-10-01
**Maintained By:** Claude Code (LLM Agent)

---

# Local CI/CD Validation Setup

## Overview

This section describes local validation tools that replicate GitHub Actions CI/CD checks. Running these tools before committing ensures code passes remote checks, saving time and preventing failed builds.

## Problem Statement

GitHub Actions CI/CD pipeline was failing on feature branches due to:
1. **Test Collection Errors**: Obsolete test files trying to import deleted modules
2. **Type Checking Failures**: Missing type annotations
3. **Formatting Issues**: Inconsistent code formatting (black, isort)
4. **Coverage Requirements**: Code coverage below 85% threshold

**Impact**: Every push triggered a failed build, slowing development velocity.

## Solution: Local Validation Tools

Two complementary tools mirror the GitHub Actions pipeline:

### 1. Pre-Commit Hook (`.git/hooks/pre-commit`)

**Purpose**: Automatically validate code quality before every commit

**What it does**:
- ✅ Runs black (code formatter check)
- ✅ Runs isort (import sorting check)
- ✅ Runs flake8 (style guide enforcement)
- ✅ Runs mypy (static type checking)

**When it runs**: Automatically on `git commit`

**How to skip** (not recommended): `git commit --no-verify`

### 2. Full CI Check Script (`scripts/run-ci-checks.sh`)

**Purpose**: Run complete CI/CD pipeline locally before pushing

**What it does**:
- ✅ **Phase 1 - Linting**: black, isort, flake8
- ✅ **Phase 2 - Type Checking**: mypy
- ✅ **Phase 3 - Tests & Coverage**: pytest with 85% coverage requirement
- ✅ **Phase 4 - Security**: bandit, safety

**How to run**:
```bash
./scripts/run-ci-checks.sh
```

## GitHub Actions Pipeline Mapping

Local tools replicate exact checks from `.github/workflows/ci.yml`:

| GitHub Job | Local Tool | Coverage |
|------------|------------|----------|
| `lint` | Pre-commit hook + run-ci-checks.sh | black, isort, flake8 |
| `type-check` | Pre-commit hook + run-ci-checks.sh | mypy |
| `test` | run-ci-checks.sh | pytest with 85% coverage |
| `security` | run-ci-checks.sh | bandit, safety |

## Daily Workflow

### Before Committing
Pre-commit hook runs automatically. If it fails:

```bash
# Fix formatting
black src/ tests/
isort src/ tests/

# Fix type errors
mypy src/ --install-types --non-interactive

# Then commit again
git commit -m "Your message"
```

### Before Pushing
Run the full CI pipeline locally:

```bash
./scripts/run-ci-checks.sh
```

If it passes, your code will pass GitHub Actions ✅

### Quick Fixes

```bash
# Auto-fix formatting
black src/ tests/
isort src/ tests/

# Check types
mypy src/ --install-types --non-interactive

# Run tests
pytest --cov=src --cov-fail-under=85 -v
```

## Benefits

1. **Fast Feedback**: Catch issues in seconds, not minutes
2. **Confidence**: Know code will pass CI before pushing
3. **Productivity**: No more waiting for remote builds to fail
4. **Consistency**: Same checks locally and remotely

## Troubleshooting

### Pre-commit hook doesn't run
```bash
chmod +x .git/hooks/pre-commit
```

### "Command not found" errors
```bash
source venv/bin/activate
pip install -r requirements-dev.txt
```

### Tests fail locally but pass in CI
```bash
# Check environment variables
echo $DATABASE_URL

# Ensure database is running
docker-compose up -d postgres
```

---

**Added**: 2025-10-01
**Status**: Active ✅

---

# E2E Testing Strategy with Testcontainers

## Overview

This section documents the E2E testing strategy using Testcontainers-Python for REST API testing with full PostgreSQL + pgvector stack. This approach follows the **Testing Pyramid** principle to balance test coverage, execution speed, and realistic integration testing.

## Testing Pyramid Principle

### Distribution Target

```
      /\
     /E2E\      ~10 tests  - Critical user journeys only (3%)
    /------\
   /Integr-\   ~90 tests  - Service layer + SQLite (30%)
  /----------\
 /   Unit    \ ~200 tests - Business logic, validation (67%)
/-------------\

Total: ~300 tests
```

### Key Principles

1. **Unit Tests (67%)**: Fast, isolated tests of business logic
   - Pure functions, validators, utilities
   - No database or external dependencies
   - Microsecond execution time
   - Written for every new function/method

2. **Integration Tests (30%)**: Service layer tests with SQLite
   - Test service methods with in-memory database
   - Fast execution (~2-3 seconds for all tests)
   - Comprehensive coverage of business logic
   - Use existing `tests/test_*.py` structure

3. **E2E Tests (3%)**: Full stack tests with real infrastructure
   - FastAPI + PostgreSQL + pgvector in Docker containers
   - Test critical user journeys end-to-end
   - Catch integration issues SQLite tests miss
   - Slower execution (~30-60 seconds total)
   - **MINIMAL COUNT**: Only ~10 tests for highest-value scenarios

## Why Testcontainers?

### Problem with SQLite-Only Testing

Integration tests use SQLite for speed, but this creates gaps:
- Missing PostgreSQL-specific features (recursive CTEs, JSONB operators)
- No pgvector extension testing
- Different SQL dialects may cause production issues
- No realistic network/connection testing

### Solution: E2E Tests with Testcontainers

**Testcontainers-Python** provides:
- Programmatic Docker container management
- Automatic cleanup after tests
- Session-scoped fixtures for performance
- CI/CD friendly (Docker-in-Docker support)
- Full PostgreSQL + pgvector stack for realistic testing

### Alternative Considered: pytest-docker-compose

We chose Testcontainers over pytest-docker-compose because:
- Better programmatic control over container lifecycle
- Easier isolation between test runs
- More flexible fixture architecture
- Better documentation and community support

## Implementation Architecture

### Project Structure

```
src/
├── api/
│   ├── main.py                 # FastAPI app
│   ├── dependencies.py         # Dependency injection (get_db)
│   └── v1/
│       ├── documents.py        # Document endpoints
│       ├── relationships.py    # Relationship endpoints
│       └── models/
│           ├── document.py     # Pydantic request/response models
│           └── relationship.py

tests/
├── unit/                       # Pure functions, utilities
├── integration/                # Service + SQLite (current tests)
│   ├── test_relationship_service.py
│   └── test_hierarchy_traversal.py
└── e2e/                        # Full stack + Testcontainers
    ├── conftest.py            # Container fixtures
    ├── test_e2e_documents.py
    └── test_e2e_workflows.py
```

### Testcontainers Setup (tests/e2e/conftest.py)

```python
import pytest
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.main import app
from src.api.dependencies import get_db
from src.database.base import Base

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL + pgvector container for entire test session."""
    with PostgresContainer("pgvector/pgvector:pg15") as postgres:
        # Run migrations
        engine = create_engine(postgres.get_connection_url())
        Base.metadata.create_all(engine)
        yield postgres

@pytest.fixture
def test_db(postgres_container):
    """Create database session for each test."""
    engine = create_engine(postgres_container.get_connection_url())
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()  # Rollback changes after test
        db.close()

@pytest.fixture
def api_client(test_db):
    """Create FastAPI test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

### E2E Test Example

```python
# tests/e2e/test_e2e_workflows.py
def test_e2e_create_document_hierarchy(api_client, test_db):
    """
    E2E: Create full hierarchy and verify all relationships.

    Critical path covering:
    - Document creation via API
    - Relationship creation
    - Breadcrumb generation
    - Parent context aggregation
    """
    # Create Vision via API
    vision_response = api_client.post("/api/v1/documents", json={
        "user_id": str(uuid.uuid4()),
        "document_type": "vision_document",
        "title": "Product Vision 2024",
        "content_markdown": "Our vision is to..."
    })
    assert vision_response.status_code == 201
    vision_id = vision_response.json()["id"]

    # Create Feature under Vision
    feature_response = api_client.post("/api/v1/documents", json={
        "user_id": str(uuid.uuid4()),
        "document_type": "feature_document",
        "title": "User Authentication",
        "content_markdown": "This feature provides..."
    })
    feature_id = feature_response.json()["id"]

    # Create relationship via API
    rel_response = api_client.post("/api/v1/relationships", json={
        "parent_id": vision_id,
        "child_id": feature_id
    })
    assert rel_response.status_code == 201

    # Verify breadcrumb via API
    breadcrumb = api_client.get(f"/api/v1/documents/{feature_id}/breadcrumb")
    assert "Product Vision 2024" in breadcrumb.json()["breadcrumb"]

    # Verify parent context (for RAG)
    context = api_client.get(f"/api/v1/documents/{feature_id}/context")
    assert "Our vision is to" in context.json()["context"]
```

## E2E Test Coverage (~10 Tests)

### Critical User Journeys

1. **test_e2e_create_document_hierarchy** - Full CRUD flow
2. **test_e2e_ripple_effect_propagation** - Update parent, verify descendants marked
3. **test_e2e_breadcrumb_navigation** - Deep hierarchy breadcrumb generation
4. **test_e2e_relationship_validation** - Circular dependency prevention
5. **test_e2e_parent_context_aggregation** - RAG context retrieval
6. **test_e2e_concurrent_updates** - Race condition handling
7. **test_e2e_large_document_performance** - Performance baseline
8. **test_e2e_cascade_delete** - Relationship deletion behavior
9. **test_e2e_search_filters** - Document search with filters
10. **test_e2e_full_workflow** - Vision → Feature → Epic → Story

### Performance Baselines

E2E tests establish performance expectations:
- Document creation: < 100ms
- Hierarchy traversal (10 levels): < 200ms
- Parent context aggregation: < 300ms
- Breadcrumb generation: < 50ms
- Full workflow (Vision → Story): < 1s

## CI/CD Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/ci.yml

jobs:
  test:
    name: Unit Tests & Coverage
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Run integration tests (SQLite)
        run: pytest tests/integration/ --cov=src

  e2e:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: [test]  # Run after unit/integration tests pass

    steps:
      - name: Set up Docker for Testcontainers
        run: docker info

      - name: Run E2E tests with Testcontainers
        run: pytest tests/e2e/ -v --tb=short

      - name: Upload performance metrics
        uses: actions/upload-artifact@v4
        with:
          name: e2e-performance
          path: e2e-metrics.json
```

### Test Execution Strategy

1. **Run integration tests first** (fast, comprehensive)
2. **Only run E2E if integration passes** (fail fast)
3. **Allow E2E to be skipped on draft PRs** (optional flag)
4. **Track E2E performance metrics over time** (regression detection)

## FastAPI Endpoint Pattern

### Document CRUD Endpoint Example

```python
# src/api/v1/documents.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.services.document_service import DocumentService
from src.api.v1.models.document import DocumentCreate, DocumentResponse

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

@router.post("/", response_model=DocumentResponse, status_code=201)
def create_document(
    document: DocumentCreate,
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    doc = service.create_document(
        user_id=document.user_id,
        document_type=document.document_type,
        title=document.title,
        content_markdown=document.content_markdown
    )
    return doc

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    service = DocumentService(db)
    doc = service.get_document(uuid.UUID(document_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
```

### Dependency Injection (src/api/dependencies.py)

```python
from sqlalchemy.orm import Session
from src.database.base import SessionLocal

def get_db():
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Best Practices

### When to Write E2E Tests

✅ **DO write E2E tests for:**
- Critical user workflows (document creation → relationship → retrieval)
- Integration points between major components
- Features requiring PostgreSQL-specific functionality
- Performance-critical operations
- Security-sensitive endpoints (authentication, authorization)

❌ **DON'T write E2E tests for:**
- Edge cases (use integration tests instead)
- Input validation (use unit tests)
- Error handling (use integration tests)
- Business logic (use unit tests)
- Individual service methods (use integration tests)

### Test Data Management

```python
# Use fixtures for common test data
@pytest.fixture
def sample_documents(api_client):
    """Create standard document hierarchy for testing."""
    vision = api_client.post("/api/v1/documents", json={...}).json()
    feature = api_client.post("/api/v1/documents", json={...}).json()
    return {"vision": vision, "feature": feature}

# Each test should clean up after itself (use test_db fixture with rollback)
```

### Performance Optimization

1. **Session-scoped container**: Start PostgreSQL once per test session
2. **Transaction rollback**: Rollback database changes after each test
3. **Parallel execution**: Run E2E tests in parallel when possible
4. **Selective execution**: Skip E2E on draft PRs with flag

## Troubleshooting

### Container startup fails in CI

```yaml
# Ensure Docker-in-Docker is available
steps:
  - name: Set up Docker
    run: docker info
```

### Tests are flaky

```python
# Use proper wait strategies
from testcontainers.core.waiting_utils import wait_for_logs

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("pgvector/pgvector:pg15") as postgres:
        wait_for_logs(postgres, "database system is ready to accept connections")
        yield postgres
```

### Database state persists between tests

```python
# Ensure proper rollback in test_db fixture
@pytest.fixture
def test_db(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()  # Critical: rollback changes
        db.close()
```

## Migration from SQLite-Only Testing

### Before (All SQLite)

```python
tests/
├── test_document_service.py
├── test_relationship_service.py
└── test_hierarchy_traversal.py
```

### After (Pyramid Structure)

```python
tests/
├── unit/                          # New: Pure functions
│   ├── test_validators.py
│   └── test_formatters.py
├── integration/                   # Keep existing
│   ├── test_document_service.py
│   ├── test_relationship_service.py
│   └── test_hierarchy_traversal.py
└── e2e/                          # New: Full stack
    ├── conftest.py
    ├── test_e2e_workflows.py
    └── test_e2e_performance.py
```

### Migration Steps

1. **Keep all existing integration tests** - They're valuable and fast
2. **Add E2E tests gradually** - Start with 1-2 critical paths
3. **Extract pure functions to unit tests** - As you refactor
4. **Monitor test execution time** - Adjust pyramid if E2E gets too slow

## Summary

### Key Takeaways

1. **Follow the pyramid**: 67% unit, 30% integration, 3% E2E
2. **E2E tests are expensive**: Keep count minimal (~10 tests)
3. **Use Testcontainers for realism**: Full PostgreSQL + pgvector stack
4. **Integration tests are your workhorse**: Fast + comprehensive
5. **CI/CD runs E2E separately**: Fail fast on integration tests first

### Resources

- **Testcontainers Python**: https://testcontainers-python.readthedocs.io/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **Testing Pyramid**: https://martinfowler.com/articles/practical-test-pyramid.html

---

**Added**: 2025-10-01
**Status**: Active ✅
