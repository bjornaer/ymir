#!/bin/bash
# Quick validation script for Ymir

set -e

echo "========================================="
echo "Ymir Validation Script"
echo "========================================="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}✗ Poetry is not installed${NC}"
    echo "Install from: https://python-poetry.org/docs/#installation"
    exit 1
fi
echo -e "${GREEN}✓ Poetry found${NC}"

# Install dependencies
echo
echo "Installing dependencies..."
poetry install --no-interaction || {
    echo -e "${RED}✗ Failed to install dependencies${NC}"
    exit 1
}
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run linters
echo
echo "Running linters..."
echo "  - Black..."
poetry run black . --check --quiet && echo -e "${GREEN}  ✓ Black passed${NC}" || echo -e "${YELLOW}  ⚠ Black found issues (run 'poetry run black .' to fix)${NC}"

echo "  - isort..."
poetry run isort . --check-only --quiet && echo -e "${GREEN}  ✓ isort passed${NC}" || echo -e "${YELLOW}  ⚠ isort found issues (run 'poetry run isort .' to fix)${NC}"

echo "  - Ruff..."
poetry run ruff check . --quiet && echo -e "${GREEN}  ✓ Ruff passed${NC}" || echo -e "${YELLOW}  ⚠ Ruff found issues${NC}"

# Run tests
echo
echo "Running tests..."
poetry run pytest -v --tb=short || {
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ All tests passed${NC}"

# Run tests with coverage
echo
echo "Checking test coverage..."
poetry run pytest --cov=ymir --cov-report=term-missing --cov-report=html --quiet
echo -e "${GREEN}✓ Coverage report generated (see htmlcov/index.html)${NC}"

# Test CLI
echo
echo "Testing CLI..."
poetry run ymir --version &> /dev/null && echo -e "${GREEN}✓ CLI works${NC}" || echo -e "${RED}✗ CLI failed${NC}"

# Test example script
echo
echo "Testing example script..."
poetry run ymir run examples/simple_example.ymr &> /dev/null && echo -e "${GREEN}✓ Example script ran successfully${NC}" || echo -e "${YELLOW}⚠ Example script had issues${NC}"

# Summary
echo
echo "========================================="
echo -e "${GREEN}✓ Validation Complete!${NC}"
echo "========================================="
echo
echo "Next steps:"
echo "  - View coverage: open htmlcov/index.html"
echo "  - Run specific tests: poetry run pytest tests/core/test_cli.py -v"
echo "  - Build executable: poetry run python scripts/build_executable.py"
echo "  - Format code: poetry run black . && poetry run isort ."
echo

