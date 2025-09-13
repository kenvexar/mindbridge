#!/bin/bash

# MindBridge Cloud Run 完全自動デプロイスクリプト
# Usage: ./scripts/deploy.sh [PROJECT_ID] [REGION]

set -euo pipefail

# Configuration
PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION=${2:-us-central1}
SERVICE_NAME="mindbridge"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/mindbridge/mindbridge"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Validate prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed. Please install Google Cloud SDK."
    fi

    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker."
    fi

    if [[ -z "$PROJECT_ID" ]]; then
        error "PROJECT_ID is not set. Please provide it as an argument or configure gcloud."
    fi

    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 &> /dev/null; then
        error "Not authenticated with gcloud. Run: gcloud auth login"
    fi

    log "Prerequisites check passed ✓"
}

# Enable required APIs
enable_apis() {
    log "Enabling required Google Cloud APIs..."

    gcloud services enable \
        run.googleapis.com \
        cloudbuild.googleapis.com \
        artifactregistry.googleapis.com \
        secretmanager.googleapis.com \
        --project="$PROJECT_ID"

    log "APIs enabled ✓"
}

# Ensure Artifact Registry repository exists
ensure_artifact_registry_repo() {
    log "Ensuring Artifact Registry repository exists..."
    if ! gcloud artifacts repositories describe mindbridge \
        --location="$REGION" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        gcloud artifacts repositories create mindbridge \
            --repository-format=docker \
            --location="$REGION" \
            --description="MindBridge container images" \
            --project="$PROJECT_ID"
        log "Artifact Registry repository 'mindbridge' created ✓"
    else
        log "Artifact Registry repository 'mindbridge' already exists ✓"
    fi
}

# Create secrets if they don't exist
create_secrets() {
    log "Checking secrets..."

    if ! gcloud secrets describe discord-bot-token --project="$PROJECT_ID" &>/dev/null; then
        warn "discord-bot-token secret not found. Please create it manually:"
        echo "  echo -n 'YOUR_DISCORD_TOKEN' | gcloud secrets create discord-bot-token --data-file=-"
    fi

    if ! gcloud secrets describe gemini-api-key --project="$PROJECT_ID" &>/dev/null; then
        warn "gemini-api-key secret not found. Please create it manually:"
        echo "  echo -n 'YOUR_GEMINI_API_KEY' | gcloud secrets create gemini-api-key --data-file=-"
    fi
}

# Create service account
create_service_account() {
    local SA_NAME="mindbridge-service"
    local SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

    log "Creating service account..."

    if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
        gcloud iam service-accounts create "$SA_NAME" \
            --display-name="Mindbridge Service Account" \
            --project="$PROJECT_ID"
    fi

    # Grant necessary permissions
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor"

    log "Service account configured ✓"
}

# Deploy using Cloud Build (推奨方法)
deploy_with_cloud_build() {
    log "Cloud Build でデプロイ開始..."

    # cloudbuild.yaml の場所を解決（deploy/ 優先 → ルート）
    local CB_CONFIG=""
    if [[ -f "deploy/cloudbuild.yaml" ]]; then
        CB_CONFIG="deploy/cloudbuild.yaml"
    elif [[ -f "cloudbuild.yaml" ]]; then
        CB_CONFIG="cloudbuild.yaml"
    else
        error "cloudbuild.yaml が見つかりません。deploy/ またはプロジェクトルートを確認してください。"
    fi

    # Cloud Build でデプロイ
    local BUILD_ID
    BUILD_ID=$(gcloud builds submit --config "$CB_CONFIG" --format="value(id)")

    if [[ $? -eq 0 ]]; then
        log "Cloud Build デプロイ完了 ✓ (Build ID: $BUILD_ID)"
    else
        error "Cloud Build デプロイ失敗"
    fi
}

# Deploy to Cloud Run
deploy_service() {
    local GIT_SHA=$(git rev-parse --short HEAD || echo "unknown")

    log "Deploying to Cloud Run..."

    # cloud-run.yaml の場所を解決（deploy/ 優先 → ルート）
    local CR_CONFIG=""
    if [[ -f "deploy/cloud-run.yaml" ]]; then
        CR_CONFIG="deploy/cloud-run.yaml"
    elif [[ -f "cloud-run.yaml" ]]; then
        CR_CONFIG="cloud-run.yaml"
    else
        error "cloud-run.yaml が見つかりません。deploy/ またはプロジェクトルートを確認してください。"
    fi

    # Replace placeholder in resolved yaml (後方互換: PROJECT_ID が無い場合はそのまま)
    if grep -q "PROJECT_ID" "$CR_CONFIG"; then
        sed "s/PROJECT_ID/$PROJECT_ID/g" "$CR_CONFIG" > /tmp/cloud-run-deploy.yaml
    else
        cp "$CR_CONFIG" /tmp/cloud-run-deploy.yaml
    fi

    # Deploy the service
    gcloud run services replace /tmp/cloud-run-deploy.yaml \
        --region="$REGION" \
        --project="$PROJECT_ID"

    # Update with the specific image
    gcloud run services update "$SERVICE_NAME" \
        --image="${IMAGE_NAME}:${GIT_SHA}" \
        --region="$REGION" \
        --project="$PROJECT_ID"

    # Clean up temp file
    rm -f /tmp/cloud-run-deploy.yaml

    log "Service deployed ✓"
}

# Get service URL
get_service_url() {
    local URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='value(status.url)')

    log "Service URL: $URL"
    echo -e "${BLUE}Health Check: ${URL}/health${NC}"
}

# Test deployment
test_deployment() {
    log "Testing deployment..."

    local URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='value(status.url)')

    # Wait for service to be ready
    sleep 30

    if curl -f "${URL}/health" &>/dev/null; then
        log "Health check passed ✓"
    else
        warn "Health check failed. Check the logs:"
        echo "  gcloud logs read --project=$PROJECT_ID --limit=50 --service=$SERVICE_NAME"
    fi
}

# Main deployment process
main() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  Mindbridge Cloud Run Deployment${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo
    echo "Project ID: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Service: $SERVICE_NAME"
    echo

    check_prerequisites
    enable_apis
    ensure_artifact_registry_repo
    create_secrets
    create_service_account
    deploy_with_cloud_build
    get_service_url
    test_deployment

    echo
    echo -e "${GREEN}🚀 Deployment completed successfully!${NC}"
    echo
    echo "Next steps:"
    echo "1. Configure your Discord bot settings"
    echo "2. Set up your Obsidian vault path"
    echo "3. Test the bot functionality"
    echo
    echo "Useful commands:"
    echo "  View logs: gcloud logs tail --project=$PROJECT_ID --service=$SERVICE_NAME"
    echo "  Update service: gcloud run services update $SERVICE_NAME --region=$REGION"
    echo "  Delete service: gcloud run services delete $SERVICE_NAME --region=$REGION"
}

# Run main function
main "$@"
