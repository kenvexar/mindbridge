#!/bin/bash

# Google Cloud Secrets Setup Script
# Usage: ./scripts/setup-secrets.sh [PROJECT_ID]

set -euo pipefail

PROJECT_ID=${1:-$(gcloud config get-value project)}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

prompt_secret() {
    local secret_name=$1
    local description=$2

    echo -e "${BLUE}Setting up: ${secret_name}${NC}"
    echo "Description: $description"
    echo -n "Enter the value (input will be hidden): "

    # Read secret value without echoing
    read -s secret_value
    echo # New line after hidden input

    if [[ -z "$secret_value" ]]; then
        warn "Empty value provided for $secret_name. Skipping..."
        return 1
    fi

    # Create or update secret
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        log "Updating existing secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
            --data-file=- --project="$PROJECT_ID"
    else
        log "Creating new secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --data-file=- --project="$PROJECT_ID"
    fi

    log "Secret $secret_name configured successfully ✓"
    echo
}

main() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  Mindbridge Secrets Setup${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo
    echo "Project ID: $PROJECT_ID"
    echo

    # Check if gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 &> /dev/null; then
        error "Not authenticated with gcloud. Run: gcloud auth login"
    fi

    # Enable Secret Manager API
    log "Enabling Secret Manager API..."
    gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"

    # Set up secrets
    echo "Setting up required secrets for Mindbridge..."
    echo

    prompt_secret "discord-bot-token" "Discord bot token from Discord Developer Portal"
    prompt_secret "discord-guild-id" "Discord Guild ID (Server ID) where the bot will operate"
    prompt_secret "gemini-api-key" "Google Gemini API key from Google AI Studio"
    prompt_secret "garmin-username" "Garmin Connect username/email"
    prompt_secret "garmin-password" "Garmin Connect password"
    prompt_secret "github-token" "GitHub Personal Access Token for vault backup"
    prompt_secret "obsidian-backup-repo" "GitHub repository URL for Obsidian vault backup (e.g., https://github.com/username/obsidian-vault.git)"

    # Optional secrets
    echo -e "${YELLOW}Optional secrets (press Enter to skip):${NC}"
    echo

    if prompt_secret "google-cloud-speech-credentials" "Google Cloud Speech-to-Text service account JSON (paste the entire JSON content)" 2>/dev/null; then
        log "Google Cloud Speech credentials configured"
    fi

    # Set up IAM permissions
    log "Setting up IAM permissions..."

    SERVICE_ACCOUNT="mindbridge-service@${PROJECT_ID}.iam.gserviceaccount.com"

    # Grant access to secrets
    for secret in "discord-bot-token" "discord-guild-id" "gemini-api-key" "garmin-username" "garmin-password" "github-token" "obsidian-backup-repo" "google-cloud-speech-credentials"; do
        if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
            gcloud secrets add-iam-policy-binding "$secret" \
                --member="serviceAccount:$SERVICE_ACCOUNT" \
                --role="roles/secretmanager.secretAccessor" \
                --project="$PROJECT_ID" 2>/dev/null || true
        fi
    done

    echo
    echo -e "${GREEN}✅ Secrets setup completed!${NC}"
    echo
    echo "Configured secrets:"
    gcloud secrets list --project="$PROJECT_ID" --format="table(name,createTime)"
    echo
    echo "Next steps:"
    echo "1. Run: ./scripts/deploy.sh $PROJECT_ID"
    echo "2. Configure your Discord bot settings"
    echo "3. Test the deployment"
}

main "$@"
