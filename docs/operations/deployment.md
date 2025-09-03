# 🚀 デプロイメントガイド

MindBridge の本番環境への安全で効率的なデプロイメント手順を説明します。

## 📋 目次

1. [デプロイメント戦略](#デプロイメント戦略)
2. [Google Cloud Run デプロイメント](#google-cloud-run-デプロイメント)
3. [Docker デプロイメント](#docker-デプロイメント)
4. [VPS デプロイメント](#vps-デプロイメント)
5. [継続的デプロイメント (CI/CD)](#継続的デプロイメント-cicd)
6. [環境別設定](#環境別設定)
7. [セキュリティ考慮事項](#セキュリティ考慮事項)
8. [監視とログ](#監視とログ)
9. [ロールバック手順](#ロールバック手順)

## 🎯 デプロイメント戦略

### 環境アーキテクチャ

```
Development → Staging → Production
     ↓           ↓          ↓
  [Local]   [Cloud Run] [Cloud Run]
             [Testing]   [Production]
```

### デプロイメント原則

1. **Infrastructure as Code**: 全設定をコード化
2. **Immutable Deployments**: 不変なデプロイメント
3. **Blue-Green Deployment**: ダウンタイムなしデプロイ
4. **Automated Rollback**: 自動ロールバック機能
5. **Security First**: セキュリティを最優先

## ☁️ Google Cloud Run デプロイメント

### 前提条件

```bash
# Google Cloud CLI のインストールと認証
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 1. プロジェクト初期設定

```bash
# プロジェクト変数設定
export PROJECT_ID="discord-obsidian-bot"
export REGION="asia-northeast1"
export SERVICE_NAME="mindbridge-bot"

# プロジェクト作成（新規の場合）
gcloud projects create $PROJECT_ID --name="MindBridge"

# プロジェクト選択
gcloud config set project $PROJECT_ID

# 必要な API を有効化
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  containerregistry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

### 2. Secret Manager 設定

```bash
# Discord Bot Token
gcloud secrets create discord-bot-token \
  --data-file=<(echo -n "$DISCORD_BOT_TOKEN")

# Gemini API Key
gcloud secrets create gemini-api-key \
  --data-file=<(echo -n "$GEMINI_API_KEY")

# Discord Guild ID
gcloud secrets create discord-guild-id \
  --data-file=<(echo -n "$DISCORD_GUILD_ID")

# Speech API Service Account (オプション)
gcloud secrets create google-speech-credentials \
  --data-file=/path/to/service-account-key.json

# Garmin 認証情報 (オプション)
gcloud secrets create garmin-email \
  --data-file=<(echo -n "$GARMIN_EMAIL")
gcloud secrets create garmin-password \
  --data-file=<(echo -n "$GARMIN_PASSWORD")
```

### 3. IAM 権限設定

```bash
# Compute Engine デフォルトサービスアカウントを取得
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export COMPUTE_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

# Secret Manager アクセス権限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/secretmanager.secretAccessor"

# Cloud Storage アクセス権限（バックアップ用）
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/storage.objectAdmin"

# Logging 権限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/logging.logWriter"
```

### 4. Cloud Build 設定

`cloudbuild.yaml`:
```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/${_SERVICE_NAME}:$BUILD_ID',
      '-t', 'gcr.io/$PROJECT_ID/${_SERVICE_NAME}:latest',
      '.'
    ]

  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/${_SERVICE_NAME}:$BUILD_ID']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/${_SERVICE_NAME}:latest']

  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '${_SERVICE_NAME}'
      - '--image=gcr.io/$PROJECT_ID/${_SERVICE_NAME}:$BUILD_ID'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--min-instances=1'
      - '--max-instances=10'
      - '--timeout=300s'
      - '--concurrency=5'
      - '--set-env-vars=ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_SECRET_MANAGER=true'

substitutions:
  _SERVICE_NAME: 'mindbridge'
  _REGION: 'asia-northeast1'

options:
  logging: CLOUD_LOGGING_ONLY
```

### 5. デプロイ実行

```bash
# Cloud Build でのデプロイ
gcloud builds submit --config cloudbuild.yaml

# または手動でのデプロイ
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300s \
  --concurrency 5 \
  --set-env-vars="ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_SECRET_MANAGER=true"
```

### 6. Cloud Run 設定の詳細

`service.yaml`:
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: mindbridge
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/cpu-throttling: "false"
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
        run.googleapis.com/vpc-access-connector: "projects/PROJECT_ID/locations/REGION/connectors/CONNECTOR_NAME"
    spec:
      containerConcurrency: 5
      timeoutSeconds: 300
      serviceAccountName: SERVICE_ACCOUNT_EMAIL
      containers:
      - image: gcr.io/PROJECT_ID/mindbridge:latest
        ports:
        - containerPort: 8080
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: GOOGLE_CLOUD_PROJECT
          value: "PROJECT_ID"
        - name: USE_SECRET_MANAGER
          value: "true"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "1"
            memory: "1Gi"
```

## 🐳 Docker デプロイメント

### Docker Compose 設定

`docker-compose.yml`:
```yaml
version: '3.8'

services:
  discord-bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mindbridge
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    env_file:
      - .env.production
    volumes:
      - ./obsidian_vault:/app/obsidian_vault:rw
      - ./logs:/app/logs:rw
      - ./backups:/app/backups:rw
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # オプション: 監視用サービス
  monitoring:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

volumes:
  obsidian_vault:
  logs:
  backups:

networks:
  default:
    driver: bridge
```

### Dockerfile の最適化

```dockerfile
# マルチステージビルド
FROM python:3.13-slim as builder

# Build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim as production

# Runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ src/
COPY README.md .

# Create necessary directories
RUN mkdir -p logs backups obsidian_vault \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Start command
CMD ["python", "-m", "src.main"]
```

### Docker デプロイ手順

```bash
# 1. 環境設定
cp .env.example .env.production
# .env.production を本番用に編集

# 2. ビルドとデプロイ
docker-compose -f docker-compose.yml up -d --build

# 3. ログ確認
docker-compose logs -f discord-bot

# 4. ヘルスチェック
curl http://localhost:8080/health
```

## 🖥️ VPS デプロイメント

### システム要件

| 項目 | 最小 | 推奨 |
|------|------|------|
| **CPU** | 1 コア | 2 コア以上 |
| **メモリ** | 1GB | 2GB 以上 |
| **ストレージ** | 10GB | 20GB 以上 |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |

### サーバーセットアップ

```bash
# 1. システム更新
sudo apt update && sudo apt upgrade -y

# 2. 必要なパッケージのインストール
sudo apt install -y \
    python3.13 \
    python3.13-venv \
    python3-pip \
    git \
    curl \
    nginx \
    certbot \
    python3-certbot-nginx \
    htop \
    ufw

# 3. uv のインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 4. アプリケーション用ユーザー作成
sudo useradd -m -s /bin/bash discord-bot
sudo usermod -aG sudo discord-bot
```

### アプリケーションデプロイ

```bash
# 1. アプリケーションユーザーに切り替え
sudo su - discord-bot

# 2. アプリケーションのクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 3. 依存関係のインストール
uv sync

# 4. 環境設定
cp .env.example .env.production
# .env.production を編集

# 5. systemd サービス設定
sudo tee /etc/systemd/system/discord-bot.service > /dev/null <<EOF
[Unit]
Description=Discord Obsidian Memo Bot
After=network.target

[Service]
Type=simple
User=discord-bot
Group=discord-bot
WorkingDirectory=/home/discord-bot/mindbridge
Environment=PATH=/home/discord-bot/.local/bin
EnvironmentFile=/home/discord-bot/mindbridge/.env.production
ExecStart=/home/discord-bot/.local/bin/uv run python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. サービス有効化と開始
sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot

# 7. 状態確認
sudo systemctl status discord-bot
```

### Nginx Configuration (Health Check)

```nginx
# /etc/nginx/sites-available/discord-bot
server {
    listen 80;
    server_name your-domain.com;

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8080/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Metrics endpoint (optional, secure this properly)
    location /metrics {
        proxy_pass http://localhost:8080/metrics;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Restrict access to monitoring systems
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
    }

    # Block all other requests
    location / {
        return 404;
    }
}
```

```bash
# Enable Nginx configuration
sudo ln -s /etc/nginx/sites-available/discord-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Enable firewall
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 🔄 継続的デプロイメント (CI/CD)

### GitHub Actions ワークフロー

`.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PROJECT_ID: ${{ secrets.GOOGLE_CLOUD_PROJECT }}
  SERVICE_NAME: mindbridge
  REGION: asia-northeast1

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Install dependencies
        run: uv sync --dev

      - name: Run tests
        run: |
          uv run pytest --cov=src --cov-report=xml

      - name: Run type checking
        run: uv run mypy src/

      - name: Run linting
        run: uv run ruff check src/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Setup Google Cloud CLI
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GOOGLE_CLOUD_PROJECT }}
          service_account_key: ${{ secrets.GOOGLE_CLOUD_KEY }}
          export_default_credentials: true

      - name: Configure Docker
        run: gcloud auth configure-docker

      - name: Build and Deploy
        run: |
          gcloud builds submit --config cloudbuild.yaml \
            --substitutions=_SERVICE_NAME=$SERVICE_NAME,_REGION=$REGION

  notify:
    needs: [test, deploy]
    runs-on: ubuntu-latest
    if: always()

    steps:
      - name: Notify Discord
        if: needs.deploy.result == 'success'
        run: |
          curl -H "Content-Type: application/json" \
               -d '{"content": "✅ Deployment successful! Version: ${{ github.sha }}"}' \
               ${{ secrets.DISCORD_WEBHOOK_URL }}

      - name: Notify Discord on Failure
        if: needs.deploy.result == 'failure'
        run: |
          curl -H "Content-Type: application/json" \
               -d '{"content": "❌ Deployment failed! Check the logs."}' \
               ${{ secrets.DISCORD_WEBHOOK_URL }}
```

### Deployment Script

`scripts/deploy.sh`:
```bash
#!/bin/bash
set -euo pipefail

# 設定
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"discord-obsidian-bot"}
SERVICE_NAME="mindbridge"
REGION="asia-northeast1"

echo "🚀 Starting deployment to $PROJECT_ID"

# 1. プリデプロイメントチェック
echo "🔍 Running pre-deployment checks..."
uv run pytest
uv run mypy src/
uv run ruff check src/

# 2. ビルドとプッシュ
echo "🏗️ Building and pushing container..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# 3. デプロイ
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region $REGION \
  --platform managed \
  --quiet

# 4. ヘルスチェック
echo "🏥 Health check..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
curl -f $SERVICE_URL/health

echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: $SERVICE_URL"
```

## 🔧 環境別設定

### Development

```env
ENVIRONMENT=development
LOG_LEVEL=DEBUG
ENABLE_MOCK_MODE=true
OBSIDIAN_VAULT_PATH=./test_vault
```

### Staging

```env
ENVIRONMENT=staging
LOG_LEVEL=INFO
USE_SECRET_MANAGER=true
GOOGLE_CLOUD_PROJECT=discord-bot-staging
```

### Production

```env
ENVIRONMENT=production
LOG_LEVEL=INFO
USE_SECRET_MANAGER=true
GOOGLE_CLOUD_PROJECT=discord-bot-production
ENABLE_MONITORING=true
AUTO_BACKUP_ENABLED=true
```

## 🔒 セキュリティ考慮事項

### 1. 秘密情報管理

```bash
# Secret Manager の使用
gcloud secrets create my-secret --data-file=secret.txt

# 環境変数での直接指定を避ける
# ❌ Bad
DISCORD_BOT_TOKEN=MTAx...

# ✅ Good
USE_SECRET_MANAGER=true
GOOGLE_CLOUD_PROJECT=my-project
```

### 2. ネットワークセキュリティ

```bash
# VPC Connector の設定（オプション）
gcloud compute networks vpc-access connectors create my-connector \
  --network default \
  --region asia-northeast1 \
  --range 10.8.0.0/28

# Cloud Run での VPC 使用
gcloud run services update $SERVICE_NAME \
  --vpc-connector my-connector \
  --region $REGION
```

### 3. アクセス制御

```yaml
# Cloud Run での IAM ポリシー
bindings:
- members:
  - serviceAccount:bot-service-account@project.iam.gserviceaccount.com
  role: roles/run.invoker
```

## 📊 監視とログ

### Cloud Logging 設定

```bash
# ログベースメトリクスの作成
gcloud logging metrics create discord_bot_errors \
  --description="Discord bot error count" \
  --log-filter='resource.type="cloud_run_revision" AND severity>=ERROR'

# アラートポリシーの作成
gcloud alpha monitoring policies create --policy-from-file=alert-policy.yaml
```

`alert-policy.yaml`:
```yaml
displayName: "MindBridge Bot Error Alert"
conditions:
  - displayName: "Error rate too high"
    conditionThreshold:
      filter: 'metric.type="logging.googleapis.com/user/discord_bot_errors"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 5
      duration: 300s
notificationChannels:
  - projects/PROJECT_ID/notificationChannels/CHANNEL_ID
```

### ヘルスチェック

```python
# src/monitoring/health_server.py
from fastapi import FastAPI
import json

app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/metrics")
async def metrics():
    # Prometheus 形式のメトリクス
    return Response(
        content=generate_metrics(),
        media_type="text/plain"
    )
```

## 🔄 ロールバック手順

### 自動ロールバック

```bash
# 前のバージョンに自動ロールバック
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region $REGION
```

### 手動ロールバック

```bash
# 1. 利用可能なリビジョン確認
gcloud run revisions list --service $SERVICE_NAME --region $REGION

# 2. 特定リビジョンにロールバック
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions=REVISION_NAME=100 \
  --region $REGION

# 3. 動作確認
curl -f $SERVICE_URL/health
```

### 緊急停止手順

```bash
# サービスの完全停止
gcloud run services delete $SERVICE_NAME --region $REGION

# または最小インスタンス数を 0 に設定
gcloud run services update $SERVICE_NAME \
  --min-instances 0 \
  --max-instances 0 \
  --region $REGION
```

## ✅ デプロイメントチェックリスト

### プリデプロイメント
- [ ] 全テストが通過
- [ ] 型チェックが通過
- [ ] リンティングが通過
- [ ] 環境変数の設定確認
- [ ] シークレットの設定確認
- [ ] バックアップの取得

### ポストデプロイメント
- [ ] ヘルスチェックが通過
- [ ] ログエラーがない
- [ ] 基本機能の動作確認
- [ ] パフォーマンス確認
- [ ] 監視アラートの設定確認

### ロールバック準備
- [ ] 前バージョンのリビジョン確認
- [ ] ロールバック手順の確認
- [ ] 緊急連絡先の確認

---

このデプロイメントガイドに従って、安全で確実な本番環境デプロイメントを実行してください。問題が発生した場合は、トラブルシューティングガイドも併せて参照してください。
