# Deployment Guide

Safe and efficient deployment procedures for MindBridge to production environments.

## Table of Contents

1. [Deployment Strategy](#deployment-strategy)
2. [Google Cloud Run Deployment](#google-cloud-run-deployment)
3. [Docker Deployment](#docker-deployment)
4. [VPS Deployment](#vps-deployment)
5. [Continuous Deployment (CI/CD)](#continuous-deployment-cicd)
6. [Environment-specific Configuration](#environment-specific-configuration)
7. [Security Considerations](#security-considerations)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Rollback Procedures](#rollback-procedures)

## 🎯 Deployment Strategy

### Environment Architecture

```
Development → Staging → Production
     ↓           ↓          ↓
  [Local]   [Cloud Run] [Cloud Run]
             [Testing]   [Production]
```

### Deployment Principles

1. **Infrastructure as Code**: All configuration codified
2. **Immutable Deployments**: Immutable deployment artifacts
3. **Blue-Green Deployment**: Zero-downtime deployments
4. **Automated Rollback**: Automatic rollback capabilities
5. **Security First**: Security as top priority

## ☁️ Google Cloud Run Deployment

### Prerequisites

```bash
# Install and authenticate Google Cloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 1. Project Initial Setup

```bash
# Project variables
export PROJECT_ID="mindbridge-bot-prod"
export REGION="us-central1"
export SERVICE_NAME="mindbridge-bot"

# Create project (if new)
gcloud projects create $PROJECT_ID --name="MindBridge Bot"

# Select project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  containerregistry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

### 2. Secret Manager Configuration

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

# Obsidian Vault Path (if using cloud storage)
gcloud secrets create obsidian-vault-path \
  --data-file=<(echo -n "$OBSIDIAN_VAULT_PATH")

# Optional: Garmin credentials
gcloud secrets create garmin-email \
  --data-file=<(echo -n "$GARMIN_EMAIL")
gcloud secrets create garmin-password \
  --data-file=<(echo -n "$GARMIN_PASSWORD")
```

### 3. Cloud Build Configuration

`cloudbuild.yaml`:
```yaml
steps:
  # Build container image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/mindbridge-bot:$COMMIT_SHA',
      '-t', 'gcr.io/$PROJECT_ID/mindbridge-bot:latest',
      '.'
    ]

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/mindbridge-bot:$COMMIT_SHA']

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'mindbridge-bot'
      - '--image=gcr.io/$PROJECT_ID/mindbridge-bot:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--set-env-vars=ENVIRONMENT=production'
      - '--set-secrets=DISCORD_BOT_TOKEN=discord-bot-token:latest'
      - '--set-secrets=GEMINI_API_KEY=gemini-api-key:latest'
      - '--set-secrets=DISCORD_GUILD_ID=discord-guild-id:latest'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--max-instances=1'
      - '--min-instances=0'
      - '--timeout=3600'

images:
  - 'gcr.io/$PROJECT_ID/mindbridge-bot:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/mindbridge-bot:latest'

options:
  logging: CLOUD_LOGGING_ONLY
```

### 4. Cloud Run Service Configuration

```bash
# Deploy to Cloud Run
gcloud run deploy mindbridge-bot \
  --image=gcr.io/$PROJECT_ID/mindbridge-bot:latest \
  --region=$REGION \
  --platform=managed \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=1 \
  --min-instances=0 \
  --timeout=3600 \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO" \
  --set-secrets="DISCORD_BOT_TOKEN=discord-bot-token:latest" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
  --set-secrets="DISCORD_GUILD_ID=discord-guild-id:latest" \
  --allow-unauthenticated
```

### 5. Health Check Setup

The application includes built-in health endpoints. Configure Cloud Run health checks:

```bash
# Update service with health check configuration
gcloud run services update mindbridge-bot \
  --region=$REGION \
  --port=8080 \
  --set-env-vars="HEALTH_CHECK_PORT=8080"
```

## 🐳 Docker Deployment

### Production Dockerfile

`Dockerfile`:
```dockerfile
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Start application
CMD ["uv", "run", "python", "-m", "src.main"]
```

### Docker Compose for Production

`docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  mindbridge-bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mindbridge-bot-prod
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - HEALTH_CHECK_PORT=8080
    env_file:
      - .env.production
    ports:
      - "8080:8080"
    volumes:
      - vault_data:/app/vault:rw
      - ./logs:/app/logs:rw
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  vault_data:
    driver: local
```

## 🖥️ VPS Deployment

### Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
  python3.13 \
  python3.13-venv \
  python3-pip \
  git \
  curl \
  nginx \
  certbot \
  python3-certbot-nginx

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Create application user
sudo useradd -m -s /bin/bash mindbridge
sudo usermod -aG sudo mindbridge
```

### Application Setup

```bash
# Switch to application user
sudo su - mindbridge

# Clone repository
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# Create production environment
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv sync --frozen

# Configure environment
cp .env.example .env.production
# Edit .env.production with production values

# Create directories
mkdir -p logs vault backups
```

### Systemd Service Configuration

`/etc/systemd/system/mindbridge.service`:
```ini
[Unit]
Description=MindBridge Discord Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=mindbridge
Group=mindbridge
WorkingDirectory=/home/mindbridge/mindbridge
Environment=PATH=/home/mindbridge/mindbridge/.venv/bin
EnvironmentFile=/home/mindbridge/mindbridge/.env.production
ExecStart=/home/mindbridge/mindbridge/.venv/bin/python -m src.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/mindbridge/mindbridge/logs /home/mindbridge/mindbridge/vault

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mindbridge
sudo systemctl start mindbridge
sudo systemctl status mindbridge
```

### Nginx Configuration

`/etc/nginx/sites-available/mindbridge`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /health {
        proxy_pass http://localhost:8080/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /metrics {
        proxy_pass http://localhost:8080/metrics;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Basic auth for metrics endpoint
        auth_basic "Metrics";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}
```

Enable site and get SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/mindbridge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

## 🔄 Continuous Deployment (CI/CD)

### GitHub Actions Workflow

`.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  PROJECT_ID: mindbridge-bot-prod
  SERVICE_NAME: mindbridge-bot
  REGION: us-central1

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
        run: pip install uv

      - name: Install dependencies
        run: uv sync --frozen

      - name: Run tests
        run: uv run pytest --cov=src

      - name: Run linting
        run: |
          uv run ruff check src/
          uv run ruff format --check src/

      - name: Type checking
        run: uv run mypy src/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4

      - name: Setup Google Cloud CLI
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ env.PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          export_default_credentials: true

      - name: Configure Docker
        run: gcloud auth configure-docker

      - name: Build and deploy
        run: |
          gcloud builds submit --config cloudbuild.yaml \
            --substitutions=_SERVICE_NAME=$SERVICE_NAME,_REGION=$REGION

      - name: Verify deployment
        run: |
          # Wait for deployment to complete
          sleep 60
          
          # Get service URL
          SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
            --region=$REGION --format='value(status.url)')
          
          # Health check
          curl -f $SERVICE_URL/health

      - name: Notification
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          channel: '#deployments'
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

## 🔧 Environment-specific Configuration

### Production Environment Variables

`.env.production`:
```env
# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json

# Discord Configuration
DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
DISCORD_GUILD_ID=${DISCORD_GUILD_ID}

# AI Configuration
GEMINI_API_KEY=${GEMINI_API_KEY}

# Obsidian Configuration
OBSIDIAN_VAULT_PATH=${OBSIDIAN_VAULT_PATH}

# Performance Settings
AI_CACHE_SIZE_MB=200
AI_CACHE_HOURS=24
ENABLE_VECTOR_SEARCH=true

# Security Settings
USE_SECRET_MANAGER=true
ENABLE_ACCESS_LOGGING=true
SECURITY_LOG_PATH=/app/logs/security.log

# Health Check
HEALTH_CHECK_PORT=8080
ENABLE_HEALTH_ENDPOINTS=true

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=8080
```

### Staging Configuration

`.env.staging`:
```env
# Environment
ENVIRONMENT=staging
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# Use staging-specific resources
DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN_STAGING}
DISCORD_GUILD_ID=${DISCORD_GUILD_ID_STAGING}
GEMINI_API_KEY=${GEMINI_API_KEY_STAGING}

# Reduced resource limits for staging
AI_CACHE_SIZE_MB=50
MAX_CONCURRENT_REQUESTS=2
```

## 🔐 Security Considerations

### Secret Management

1. **Never commit secrets to repository**
2. **Use environment-specific secret stores**
3. **Rotate secrets regularly**
4. **Implement principle of least privilege**

### Network Security

```yaml
# Cloud Run security configuration
security_policy:
  ingress: INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER
  egress:
    - allow_all_outbound: false
    - allowed_destinations:
      - "discordapp.com:443"
      - "generativelanguage.googleapis.com:443"
      - "speech.googleapis.com:443"
```

### Container Security

```dockerfile
# Security hardening in Dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser appuser

USER appuser
```

## 📊 Monitoring and Logging

### Health Check Implementation

The application includes built-in health endpoints:
- `/health` - Basic health check
- `/ready` - Readiness check
- `/metrics` - Prometheus metrics

### Logging Configuration

```python
# Production logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime) s %(name) s %(levelname) s %(message) s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/app.log",
            "formatter": "json",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}
```

### Monitoring Setup

```bash
# Set up monitoring alerts in Google Cloud
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

`monitoring-policy.yaml`:
```yaml
displayName: "MindBridge Bot Monitoring"
conditions:
  - displayName: "High Error Rate"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND resource.label.service_name="mindbridge-bot"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.1
      duration: 300s
notificationChannels:
  - projects/PROJECT_ID/notificationChannels/CHANNEL_ID
```

## 🔄 Rollback Procedures

### Automatic Rollback

Cloud Build configuration with automatic rollback:
```yaml
# Add to cloudbuild.yaml
- name: 'gcr.io/cloud-builders/gcloud'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      # Health check after deployment
      SERVICE_URL=$(gcloud run services describe mindbridge-bot \
        --region=us-central1 --format='value(status.url)')
      
      # Wait for service to be ready
      sleep 60
      
      # Health check with retries
      for i in {1..5}; do
        if curl -f $SERVICE_URL/health; then
          echo "Health check passed"
          exit 0
        fi
        echo "Health check failed, attempt $i/5"
        sleep 30
      done
      
      # Rollback to previous revision
      echo "Rolling back to previous revision"
      gcloud run services update-traffic mindbridge-bot \
        --region=us-central1 --to-revisions=LATEST=0,mindbridge-bot-prev=100
      exit 1
```

### Manual Rollback

```bash
# List revisions
gcloud run revisions list --service=mindbridge-bot --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic mindbridge-bot \
  --region=us-central1 \
  --to-revisions=mindbridge-bot-00002-xyz=100

# Verify rollback
SERVICE_URL=$(gcloud run services describe mindbridge-bot \
  --region=us-central1 --format='value(status.url)')
curl $SERVICE_URL/health
```

### Emergency Procedures

1. **Immediate Stop**: Stop the service if critical issues occur
2. **Rollback**: Revert to last known good version
3. **Investigation**: Analyze logs and metrics
4. **Fix and Redeploy**: Address issues and redeploy

```bash
# Emergency stop
gcloud run services update mindbridge-bot \
  --region=us-central1 \
  --min-instances=0 \
  --max-instances=0

# Emergency rollback
gcloud run services update-traffic mindbridge-bot \
  --region=us-central1 \
  --to-revisions=mindbridge-bot-stable=100
```

---

This deployment guide ensures reliable, secure, and maintainable production deployments of MindBridge. Follow these procedures for consistent and successful deployments.