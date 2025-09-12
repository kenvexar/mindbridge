# Personal MindBridge Docker image for Google Cloud Run (無料枠最適化)
FROM python:3.13.7-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment variables for personal use
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13.7-slim

# Install runtime dependencies including ffmpeg for audio processing
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create personal user
RUN useradd --create-home --shell /bin/bash mindbridge

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=mindbridge:mindbridge /app/.venv /app/.venv

# Copy application code
COPY --chown=mindbridge:mindbridge src/ ./src/
COPY --chown=mindbridge:mindbridge README.md ./

# Create personal directories for logs, vault, cache, config, and backups
RUN mkdir -p logs vault .cache .config backups && chown -R mindbridge:mindbridge logs vault .cache .config backups

# Copy Google Cloud credentials (if they exist) for personal use
COPY --chown=mindbridge:mindbridge speech-key.json* ./.config/

# Switch to personal user
USER mindbridge

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "src.main"]
