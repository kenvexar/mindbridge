.PHONY: setup run test lint fmt type pre-commit clean env secrets optional deploy full-deploy ar-clean

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

# Artifact Registry の古いイメージをクリーンアップ（DRY-RUN）
ar-clean:
	./scripts/manage.sh ar-clean $(PROJECT_ID) $(REGION) mindbridge mindbridge 10 30

# ---- Orchestration shortcuts ----
env:
	@if [[ -z "$(PROJECT_ID)" ]]; then echo "PROJECT_ID を指定してください (例: make env PROJECT_ID=your-proj)"; exit 1; fi
	./scripts/manage.sh env $(PROJECT_ID)

secrets:
	@if [[ -z "$(PROJECT_ID)" ]]; then echo "PROJECT_ID を指定してください (例: make secrets PROJECT_ID=your-proj)"; exit 1; fi
	./scripts/manage.sh secrets $(PROJECT_ID) $(FLAGS)

optional:
	@if [[ -z "$(PROJECT_ID)" ]]; then echo "PROJECT_ID を指定してください (例: make optional PROJECT_ID=your-proj)"; exit 1; fi
	./scripts/manage.sh optional $(PROJECT_ID)

deploy:
	@if [[ -z "$(PROJECT_ID)" ]]; then echo "PROJECT_ID を指定してください (例: make deploy PROJECT_ID=your-proj)"; exit 1; fi
	./scripts/manage.sh deploy $(PROJECT_ID) $(REGION)

full-deploy:
	@if [[ -z "$(PROJECT_ID)" ]]; then echo "PROJECT_ID を指定してください (例: make full-deploy PROJECT_ID=your-proj)"; exit 1; fi
	./scripts/manage.sh full-deploy $(PROJECT_ID) $(FLAGS)
