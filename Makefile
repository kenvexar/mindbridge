.PHONY: setup run test lint fmt type pre-commit clean

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

.PHONY: cleanup-ar

# Artifact Registry の古いイメージをクリーンアップ（DRY-RUN）
cleanup-ar:
	./scripts/cleanup-artifact-registry.sh $(PROJECT_ID) $(REGION) mindbridge mindbridge 10 30
