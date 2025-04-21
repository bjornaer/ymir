.PHONY: install test lint format clean build

install:
	poetry install

test:
	poetry run pytest tests/

lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check-only .

format:
	poetry run black .
	poetry run isort .

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .mypy_cache __pycache__ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

build:
	poetry build
