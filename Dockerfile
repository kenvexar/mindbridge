# Personal MindBridge Docker image for self-hosted/container deployments
FROM python:3.14.0-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.4 /uv /bin/uv

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
FROM python:3.14.0-slim

# セキュリティ: セキュリティアップデートを適用してからパッケージインストール
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    git \
    ffmpeg \
    # セキュリティ: セキュリティツールも含める
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    # セキュリティ: apt キャッシュと tmp ファイルもクリーンアップ
    && apt-get autoremove -y \
    && apt-get autoclean

# セキュリティ: 個人使用向けユーザー作成（より安全な設定）
RUN groupadd -r mindbridge && \
    useradd -r -g mindbridge -d /app -s /bin/bash \
    --no-log-init mindbridge

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=mindbridge:mindbridge /app/.venv /app/.venv

# Copy application code
COPY --chown=mindbridge:mindbridge src/ ./src/
COPY --chown=mindbridge:mindbridge README.md ./

# セキュリティ: 個人使用向けディレクトリ作成（適切な権限設定）
RUN mkdir -p logs vault .cache .config backups .mindbridge/integrations && \
    chown -R mindbridge:mindbridge logs vault .cache .config backups .mindbridge && \
    # セキュリティ: ディレクトリ権限を制限（個人使用向け）
    chmod 750 logs vault .cache .config backups .mindbridge

# Google Cloud Speech 認証情報などは runtime で /app/.config にマウントする

# セキュリティ: 個人ユーザーに切り替え
USER mindbridge

# 環境変数設定
ENV PATH="/app/.venv/bin:$PATH" \
    # セキュリティ: Python のハッシュランダム化を有効化
    PYTHONHASHSEED=random \
    # セキュリティ: Python の最適化を有効化
    PYTHONOPTIMIZE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "src.main"]
