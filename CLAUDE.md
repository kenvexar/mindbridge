# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Environment
```bash
# Setup development environment
uv sync --dev

# Initialize environment (interactive .env generation)
./scripts/manage.sh init

# Run locally
uv run python -m src.main

# Debug mode
uv run python -m src.main --debug
```

### Testing
```bash
# Quick test run
uv run pytest -q
# or
make test

# Coverage report
uv run pytest --cov=src --cov-report=term-missing

# HTML coverage report
uv run pytest --cov=src --cov-report=html

# Manual tests (run individually as needed)
uv run python tests/manual/quick_voice_test.py
uv run python tests/manual/test_real_voice.py
uv run python tests/manual/test_voice_memo.py
uv run python tests/manual/test_garmin_integration.py
bash tests/manual/test_manage.sh
```

### Code Quality
```bash
# Lint and format (fix automatically)
uv run ruff check . --fix && uv run ruff format .
# or
make fmt

# Type checking
uv run mypy src
# or
make type

# Pre-commit hooks (run all checks)
uv run pre-commit run --all-files
# or
make pre-commit
```

### Deployment
```bash
# Full automatic deployment to Google Cloud Run
./scripts/manage.sh full-deploy YOUR_PROJECT_ID [--with-optional]

# Individual deployment steps
make env PROJECT_ID=your-project
make secrets PROJECT_ID=your-project
make deploy PROJECT_ID=your-project
```

### Container Operations
```bash
# Run with Docker (uses .env.docker)
docker compose up -d
```

## Architecture Overview

MindBridge is an AI-powered Discord bot that captures messages and voice memos, processes them with Google Gemini AI, and saves structured notes to Obsidian with automatic categorization.

### Core Components

**Entry Point**: `src/main.py` - Initializes all systems including security, health monitoring, GitHub sync, and component management with lazy loading.

**Bot System** (`src/bot/`):
- `DiscordBot` - Main Discord client with message handling
- `MessageHandler` - Processes Discord messages and voice attachments
- Command handlers in `commands/` for various integrations

**AI Processing** (`src/ai/`):
- `AIProcessor` - Google Gemini integration for content analysis
- `AdvancedNoteAnalyzer` - Note analysis and categorization
- Template-based processing for structured output

**Obsidian Integration** (`src/obsidian/`):
- `ObsidianFileManager` - File operations and note creation
- `TemplateEngine` - YAML frontmatter and template processing
- `DailyNoteIntegration` - Daily note management
- `GitHubObsidianSync` - Cloud Run persistence via GitHub sync

**Health & Life Logging** (`src/health_analysis/`, `src/lifelog/`):
- `HealthAnalysisScheduler` - Automated health data processing
- Garmin Connect integration for fitness data
- Google Calendar integration for activity tracking

**External Integrations** (`src/integrations/`, `src/garmin/`):
- Garmin Connect (OAuth-free via python-garminconnect)
- Google Calendar sync
- Financial tracking and subscription management

### Key Patterns

**Lazy Loading**: Components use `ComponentManager` for efficient resource management with caching (AI processor: 1hr, Garmin client: 30min).

**Security**: `SecureSettingsManager` handles encrypted credential storage. All sensitive operations logged via `SecurityEventLogger`.

**Async Architecture**: Full async/await pattern with `aiohttp`, `aiofiles` for I/O operations.

**Template System**: YAML frontmatter with placeholder replacement for structured Obsidian notes.

**Error Handling**: Structured logging with `structlog`, comprehensive exception handling with context preservation.

## Development Guidelines

### Code Standards
- Python >=3.13 with type annotations required for public functions
- Use `snake_case` for functions/modules, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Line length ~88 characters (handled by ruff formatter)
- Async/await for all I/O operations
- Structured logging with `structlog` (no `print` statements)

### Testing Strategy
- Unit tests in `tests/unit/` with mocking for external dependencies
- Integration tests in `tests/integration/` for component interaction
- Manual tests in `tests/manual/` for real service validation (run individually)
- Test discovery limited to `unit/` and `integration/` in CI via pytest configuration

### Pre-commit Requirements
All changes must pass:
1. `ruff check . --fix && ruff format .`
2. `mypy src`
3. `pytest -q`
4. Pre-commit hooks including gitleaks security scanning

### Configuration Management
- Environment variables in `.env` (use `.env.example` as template)
- Docker environment in `.env.docker`
- Settings managed via `pydantic-settings` with validation
- Secrets stored encrypted in production via Google Secret Manager

### Component Architecture
- Use dependency injection pattern for testability
- Components registered with `ComponentManager` for lazy loading
- Separate concerns: AI processing, file operations, external APIs
- Interface-based design for pluggability (especially integrations)

## Production Considerations

**Cloud Run Deployment**: Automatic via `./scripts/manage.sh full-deploy` with:
- Health server on port 8080 for container health checks
- GitHub sync for vault persistence across container restarts
- Google Cloud Speech-to-Text credentials auto-generation
- Comprehensive error handling and retry mechanisms

**Monitoring**: Health server provides status endpoints. Structured logs via `structlog` for observability.

**Security**: All credentials encrypted in Secret Manager. Access logging for security events. No hardcoded secrets in code.
