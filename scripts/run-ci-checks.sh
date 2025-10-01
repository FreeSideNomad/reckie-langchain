#!/bin/bash
#
# Run all CI/CD checks locally before pushing
# This script replicates the entire GitHub Actions pipeline
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAILED=0

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Local CI/CD Pipeline Check Runner    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo "  Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt"
    exit 1
fi
echo ""

# ============================================================================
# LINTING
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}  PHASE 1: Code Linting                ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

echo "→ Black (code formatter)"
if black --check src/ tests/; then
    echo -e "${GREEN}  ✓ Black check passed${NC}"
else
    echo -e "${RED}  ✗ Black check failed${NC}"
    echo "    Fix with: black src/ tests/"
    FAILED=1
fi
echo ""

echo "→ Isort (import sorting)"
if isort --check-only src/ tests/; then
    echo -e "${GREEN}  ✓ Isort check passed${NC}"
else
    echo -e "${RED}  ✗ Isort check failed${NC}"
    echo "    Fix with: isort src/ tests/"
    FAILED=1
fi
echo ""

echo "→ Flake8 (style guide)"
if flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503; then
    echo -e "${GREEN}  ✓ Flake8 check passed${NC}"
else
    echo -e "${RED}  ✗ Flake8 check failed${NC}"
    FAILED=1
fi
echo ""

# ============================================================================
# TYPE CHECKING
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}  PHASE 2: Type Checking                ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

echo "→ Mypy (static type checking)"
if mypy src/ --install-types --non-interactive; then
    echo -e "${GREEN}  ✓ Mypy check passed${NC}"
else
    echo -e "${RED}  ✗ Mypy check failed${NC}"
    FAILED=1
fi
echo ""

# ============================================================================
# TESTS & COVERAGE
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}  PHASE 3: Tests & Coverage             ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

echo "→ Pytest (unit tests with coverage)"
if pytest \
    --cov=src \
    --cov-report=term \
    --cov-report=html \
    --cov-fail-under=85 \
    -v; then
    echo -e "${GREEN}  ✓ All tests passed with sufficient coverage${NC}"
else
    echo -e "${RED}  ✗ Tests failed or insufficient coverage${NC}"
    FAILED=1
fi
echo ""

# ============================================================================
# SECURITY
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}  PHASE 4: Security Scanning            ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

echo "→ Bandit (security linter)"
if bandit -r src/ -ll; then
    echo -e "${GREEN}  ✓ No security issues found${NC}"
else
    echo -e "${YELLOW}  ⚠ Some security warnings (non-blocking)${NC}"
fi
echo ""

echo "→ Safety (dependency vulnerabilities)"
if safety check; then
    echo -e "${GREEN}  ✓ No vulnerable dependencies${NC}"
else
    echo -e "${YELLOW}  ⚠ Some dependency warnings (non-blocking)${NC}"
fi
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
if [ $FAILED -eq 1 ]; then
    echo -e "${RED}❌ CI/CD CHECKS FAILED${NC}"
    echo ""
    echo "Please fix the issues above before pushing."
    exit 1
else
    echo -e "${GREEN}✅ ALL CI/CD CHECKS PASSED${NC}"
    echo ""
    echo "Your code is ready to push! 🚀"
    exit 0
fi
