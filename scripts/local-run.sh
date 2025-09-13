#!/usr/bin/env bash
set -euo pipefail

# Simple runner for local mode

if [[ ! -f .env ]]; then
  echo "No .env found. Run scripts/local-setup.sh first." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Setting up virtual environment via uv sync..."
  uv sync --dev
fi

echo "Starting MindBridge..."
uv run python -m src.main
