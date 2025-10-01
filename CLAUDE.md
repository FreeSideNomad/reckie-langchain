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
