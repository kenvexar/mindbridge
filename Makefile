.PHONY: setup run test lint fmt type pre-commit clean

SHELL := /bin/bash

setup:
	uv sync --dev

run:
	uv run python -m src.main

test:
	uv run pytest -q

lint:
	uv run ruff check .

fmt:
	uv run ruff check . --fix && uv run ruff format .

type:
	uv run mypy src

pre-commit:
	uv run pre-commit run --all-files

clean:
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.backup" -delete 2>/dev/null || true
	find . -name "*.bak" -delete 2>/dev/null || true
	find . -name "*~" -delete 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true
