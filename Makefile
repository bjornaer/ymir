.PHONY: install test tests test-cov test-verbose test-core test-integration test-gpu test-http test-cli test-concurrency
.PHONY: lint format clean build build-exe validate coverage run-examples help

# Installation
install:
	poetry install

install-gpu:
	poetry install --extras gpu

# Testing
test:
	poetry run pytest tests/

tests: test

test-cov:
	poetry run pytest --cov=ymir --cov-report=html --cov-report=term-missing

test-verbose:
	poetry run pytest -v

test-core:
	poetry run pytest tests/core/ -v

test-integration:
	poetry run pytest tests/integration/ -v

test-gpu:
	poetry run pytest tests/core/test_matrix_jax_backend.py -v

test-http:
	poetry run pytest tests/core/test_http.py tests/integration/test_http_integration.py -v

test-cli:
	poetry run pytest tests/core/test_cli.py -v

test-concurrency:
	poetry run pytest tests/core/test_concurrency.py tests/integration/test_concurrency_integration.py -v

# Code Quality
lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check-only .

format:
	poetry run black .
	poetry run isort .

# Coverage
coverage:
	poetry run pytest --cov=ymir --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

coverage-xml:
	poetry run pytest --cov=ymir --cov-report=xml

# Building
build:
	poetry build

build-exe:
	poetry run python scripts/build_executable.py

# Validation
validate:
	./scripts/validate_all.sh

# Run Examples
run-examples:
	@echo "Running example scripts..."
	poetry run ymir run examples/simple_example.ymr
	poetry run ymir run examples/example.ymr
	@echo "Examples completed!"

run-example:
	poetry run ymir run examples/example.ymr

# Cleanup
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .mypy_cache __pycache__ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf .venv/

# CI Commands
ci-test:
	poetry run pytest --cov=ymir --cov-report=xml --cov-report=term-missing -v

ci-lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check-only .

# Help
help:
	@echo "Ymir Development Commands"
	@echo "========================="
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install dependencies"
	@echo "  make install-gpu      Install with GPU support (JAX)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo "  make test-verbose     Run tests with verbose output"
	@echo "  make test-core        Run core tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-gpu         Run GPU/JAX backend tests"
	@echo "  make test-http        Run HTTP client/server tests"
	@echo "  make test-cli         Run CLI command tests"
	@echo "  make test-concurrency Run concurrency tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Check code style"
	@echo "  make format           Auto-format code"
	@echo ""
	@echo "Coverage:"
	@echo "  make coverage         Generate HTML coverage report"
	@echo "  make coverage-xml     Generate XML coverage report"
	@echo ""
	@echo "Building:"
	@echo "  make build            Build Python package"
	@echo "  make build-exe        Build standalone executable"
	@echo ""
	@echo "Validation:"
	@echo "  make validate         Run full validation suite"
	@echo ""
	@echo "Examples:"
	@echo "  make run-examples     Run all example scripts"
	@echo "  make run-example      Run main example script"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts"
	@echo "  make clean-all        Remove build artifacts and venv"
	@echo ""
	@echo "CI:"
	@echo "  make ci-test          Run tests for CI"
	@echo "  make ci-lint          Run linting for CI"
