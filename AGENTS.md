# Repository Guidelines

MindBridge links Discord ingestion, AI enrichment, and Obsidian export. Use the guidelines below to stay aligned with automation and deployment.

## Project Structure & Module Organization
- `src/`: Domain packages (`ai/`, `bot/`, `obsidian/`, `finance/`, `tasks/`); `main.py` boots the runtime.
- `tests/`: `unit/` and `integration/` back CI; `manual/` stores opt-in exploratory checks.
- `scripts/`: `manage.sh` wraps setup, deployment, and cleanup steps—extend it rather than adding ad-hoc scripts.
- `deploy/`, `docker-compose.yml`, `Dockerfile*`: Infrastructure templates for Cloud Run and local containers.
- `docs/`, `vault/`, `logs/`: Reference notes and encrypted artifacts; keep secrets out of Git history.

## Build, Test, and Development Commands
```bash
uv sync --dev               # Install dependencies with dev extras
uv run python -m src.main   # Launch the bridge locally
uv run pytest -q            # Run unit + integration tests
uv run pytest --cov=src     # Collect coverage during development
uv run ruff check . --fix   # Lint and auto-fix (line length ≤88)
uv run mypy src             # Static type checks
make full-deploy PROJECT_ID=...  # Scripted cloud deployment
```

## Coding Style & Naming Conventions
- Python 3.13, 4-space indentation, and type hints on public surfaces.
- Ruff enforces `E`, `F`, `UP`, `B`, `I`; rely on `ruff format` and keep lines ≤88 chars.
- Use snake_case for functions and variables, camelCase only when Discord callbacks require it.
- Configure services via `config/` Pydantic Settings instead of inline environment lookups.

## Testing Guidelines
- Mirror business rules in `tests/unit/`; name files `test_<module>_<scenario>.py` with fixtures in `conftest.py`.
- Put cross-service flows in `tests/integration/` and mark network-heavy cases for selective execution.
- Document manual or live-fire checks in PR notes and keep them under `tests/manual/`.
- Target ≥85% coverage on new code and run `uv run pytest --cov=src --cov-report=term-missing` before requesting review.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `security:`). Example: `feat: add garmin sleep ingestor pipeline`.
- PRs need a concise summary, linked issue or context, verification notes, and evidence (logs/screenshots) for workflow changes.
- Keep changes focused; squash noise locally and ensure `ruff`, `pytest`, and `mypy` succeed before review.

## Security & Configuration Tips
- Run `./scripts/manage.sh init` to scaffold `.env`; never commit generated secrets under `vault/` or `logs/`.
- Check `mise.toml` and the `Makefile` for existing task aliases before adding CLI entry points.
- Document new external dependencies in `docs/` and extend Secret Manager hooks in `scripts/manage.sh` when credentials are required.
- Configure the `SAFETY_API_KEY` GitHub secret so the security workflow can run `safety scan` without fallback.
