#!/bin/bash

# MindBridge シークレット設定スクリプト（改良版）
# Usage: ./scripts/setup-secrets.sh [PROJECT_ID] [--skip-existing] [--with-optional]
# Flags can be specified in any order

set -euo pipefail

# Parse command line arguments
PROJECT_ID=""
SKIP_EXISTING=""
WITH_OPTIONAL=""

# Check for flags in arguments
if [[ " $* " == *" --skip-existing "* ]]; then
    SKIP_EXISTING="--skip-existing"
fi

if [[ " $* " == *" --with-optional "* ]]; then
    WITH_OPTIONAL="--with-optional"
fi

# Get project ID from arguments (first non-flag argument)
for arg in "$@"; do
    if [[ "$arg" != "--skip-existing" && "$arg" != "--with-optional" ]]; then
        PROJECT_ID="$arg"
        break
    fi
done

# Set default project ID if not provided
if [[ -z "$PROJECT_ID" ]]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
fi

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

    # Check if secret already exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${YELLOW}Secret '$secret_name' already exists${NC}"

        # Check for batch skip option
        if [[ "$SKIP_EXISTING" == "--skip-existing" ]]; then
            log "Skipping $secret_name (--skip-existing specified)"
            return 0
        fi

        echo -n "Do you want to update it? (y/n): "
        read -r update_response

        if [[ ! "$update_response" =~ ^[Yy]$ ]]; then
            log "Skipping $secret_name (already configured)"
            return 0
        fi

        echo -e "${BLUE}Updating: ${secret_name}${NC}"
    else
        echo -e "${BLUE}Setting up: ${secret_name}${NC}"
    fi

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
    echo "Debug: Arguments passed: $*"
    echo "Debug: SKIP_EXISTING='$SKIP_EXISTING'"
    echo "Debug: WITH_OPTIONAL='$WITH_OPTIONAL'"

    local mode_desc="Interactive"
    if [[ "$SKIP_EXISTING" == "--skip-existing" ]]; then
        mode_desc="Skip existing secrets"
    fi
    if [[ "$WITH_OPTIONAL" == "--with-optional" ]]; then
        mode_desc="$mode_desc + Optional features enabled"
    fi

    if [[ "$SKIP_EXISTING" == "--skip-existing" ]]; then
        echo -e "${YELLOW}Mode: $mode_desc${NC}"
    else
        echo -e "${GREEN}Mode: $mode_desc${NC}"
    fi
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
    # Garmin Connect 認証情報 (python-garminconnect ライブラリ用)
    # Check if both Garmin secrets already exist
    garmin_username_exists=$(gcloud secrets describe "garmin-username" --project="$PROJECT_ID" 2>/dev/null && echo "true" || echo "false")
    garmin_password_exists=$(gcloud secrets describe "garmin-password" --project="$PROJECT_ID" 2>/dev/null && echo "true" || echo "false")

    if [[ "$garmin_username_exists" == "true" && "$garmin_password_exists" == "true" ]]; then
        echo -e "${YELLOW}Garmin Connect 認証情報は既に設定済みです${NC}"

        # Check for batch skip option
        if [[ "$SKIP_EXISTING" == "--skip-existing" ]]; then
            log "Garmin Connect 設定をスキップしました (--skip-existing specified)"
        else
            echo -n "更新しますか？ (y/n): "
            read -r garmin_update_response

            if [[ ! "$garmin_update_response" =~ ^[Yy]$ ]]; then
                log "Garmin Connect 設定をスキップしました"
            else
                prompt_secret "garmin-username" "Garmin Connect のユーザー名またはメールアドレス"
                prompt_secret "garmin-password" "Garmin Connect のパスワード"
            fi
        fi
    else
        # Auto-setup with --with-optional flag
        if [[ "$WITH_OPTIONAL" == "--with-optional" ]]; then
            log "Setting up Garmin Connect credentials (--with-optional specified)"
            prompt_secret "garmin-username" "Garmin Connect のユーザー名またはメールアドレス"
            prompt_secret "garmin-password" "Garmin Connect のパスワード"
            log "Garmin Connect 認証情報を設定しました"
        else
            echo -e "${BLUE}Garmin Connect 認証情報を設定しますか？${NC}"
            echo "健康データ統合を有効にするには、 Garmin Connect のユーザー名とパスワードが必要です。"
            echo -n "(y/n): "
            read -r garmin_response

            if [[ "$garmin_response" =~ ^[Yy]$ ]]; then
                prompt_secret "garmin-username" "Garmin Connect のユーザー名またはメールアドレス"
                prompt_secret "garmin-password" "Garmin Connect のパスワード"
                log "Garmin Connect 認証情報を設定しました"
            else
                log "Garmin Connect 統合をスキップしました"
            fi
        fi
    fi
    prompt_secret "github-token" "GitHub Personal Access Token for vault backup"
    prompt_secret "obsidian-backup-repo" "GitHub repository URL for Obsidian vault backup (e.g., https://github.com/username/obsidian-vault.git)"

    # Optional secrets
    echo -e "${YELLOW}Optional secrets (press Enter to skip):${NC}"
    echo

    # Check if Speech-to-Text credentials already exist
    speech_credentials_exist=$(gcloud secrets describe "google-cloud-speech-credentials" --project="$PROJECT_ID" 2>/dev/null && echo "true" || echo "false")

    if [[ "$speech_credentials_exist" == "true" ]]; then
        echo -e "${YELLOW}Google Cloud Speech-to-Text 認証情報は既に設定済みです${NC}"

        # Check for batch skip option
        if [[ "$SKIP_EXISTING" == "--skip-existing" ]]; then
            log "Speech-to-Text 設定をスキップしました (--skip-existing specified)"
        else
            echo -n "更新しますか？ (y/n): "
            read -r speech_update_response

            if [[ ! "$speech_update_response" =~ ^[Yy]$ ]]; then
                log "Speech-to-Text 設定をスキップしました"
            else
                echo -e "${BLUE}Speech-to-Text 認証情報を更新中...${NC}"
                echo "1. Auto-generate credentials (recommended)"
                echo "2. Manually enter JSON credentials"
                echo -n "Choose option (1/2): "
                read -r speech_choice
            fi
        fi
    else
        # Auto-setup with --with-optional flag
        if [[ "$WITH_OPTIONAL" == "--with-optional" ]]; then
            log "Setting up Speech-to-Text credentials (--with-optional specified)"
            speech_choice="1"  # Auto-generate
        else
            echo -e "${BLUE}Setting up Google Cloud Speech-to-Text credentials...${NC}"
            echo "You can either:"
            echo "1. Auto-generate credentials (recommended)"
            echo "2. Manually enter JSON credentials"
            echo "3. Skip (press Enter)"
            echo -n "Choose option (1/2/Enter): "
            read -r speech_choice
        fi
    fi

    # Only process if not skipped (when speech_choice is set)
    if [[ -n "$speech_choice" ]]; then
        case "$speech_choice" in
            1)
                log "Auto-generating Speech-to-Text credentials..."
                SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
                if [[ -f "$SCRIPT_DIR/generate-speech-credentials.sh" ]]; then
                    # Execute with timeout and capture output using json-only mode
                    log "Executing speech credentials generation script..."

                    # Cross-platform timeout implementation
                    speech_generation_with_timeout() {
                        local timeout_duration=60
                        "$SCRIPT_DIR/generate-speech-credentials.sh" "$PROJECT_ID" "json-only" > /tmp/speech_output.txt 2>/dev/null &
                        local pid=$!

                        # Wait for process with timeout
                        local count=0
                        while kill -0 $pid 2>/dev/null && [ $count -lt $timeout_duration ]; do
                            sleep 1
                            ((count++))
                        done

                        if kill -0 $pid 2>/dev/null; then
                            # Process still running, kill it
                            kill -TERM $pid 2>/dev/null
                            sleep 2
                            kill -KILL $pid 2>/dev/null
                            return 1
                        else
                            # Process completed, check exit status
                            wait $pid
                            return $?
                        fi
                    }

                    if speech_generation_with_timeout; then
                        # Extract JSON from script output (everything between markers)
                        speech_json=$(sed -n '/--- JSON 開始 ---/,/--- JSON 終了 ---/p' /tmp/speech_output.txt | sed '1d;$d')

                        # Debug: Show what we captured
                        if [[ -s /tmp/speech_output.txt ]]; then
                            log "Script output captured (first 5 lines):"
                            head -5 /tmp/speech_output.txt | while read -r line; do log "  $line"; done
                        else
                            warn "No output captured from generation script"
                        fi

                        # Validate JSON is not empty
                        if [[ -z "$speech_json" || "$speech_json" == *"error"* ]]; then
                            warn "Failed to extract valid JSON from generation script"
                            speech_json=""
                        fi

                        rm -f /tmp/speech_output.txt
                    else
                        warn "Speech credentials generation timed out or failed"
                        if [[ -f /tmp/speech_output.txt ]]; then
                            warn "Partial output captured:"
                            head -3 /tmp/speech_output.txt | while read -r line; do warn "  $line"; done
                        fi
                        rm -f /tmp/speech_output.txt
                        speech_json=""
                    fi
                    if [[ -n "$speech_json" ]]; then
                        log "Saving generated credentials to Secret Manager..."
                        if echo -n "$speech_json" | gcloud secrets create "google-cloud-speech-credentials" \
                            --project="$PROJECT_ID" --data-file=- 2>/dev/null; then
                            log "Google Cloud Speech credentials auto-generated and configured ✓"
                        elif echo -n "$speech_json" | gcloud secrets versions add "google-cloud-speech-credentials" \
                            --project="$PROJECT_ID" --data-file=- 2>/dev/null; then
                            log "Google Cloud Speech credentials auto-generated and updated ✓"
                        else
                            warn "Failed to save generated credentials to Secret Manager"
                            log "Falling back to manual entry..."
                            if prompt_secret "google-cloud-speech-credentials" "Google Cloud Speech-to-Text service account JSON (paste the entire JSON content)" 2>/dev/null; then
                                log "Google Cloud Speech credentials configured manually"
                            fi
                        fi
                    else
                        warn "Failed to auto-generate credentials, falling back to manual entry"
                        if prompt_secret "google-cloud-speech-credentials" "Google Cloud Speech-to-Text service account JSON (paste the entire JSON content)" 2>/dev/null; then
                            log "Google Cloud Speech credentials configured manually"
                        fi
                    fi
                else
                    warn "Auto-generation script not found, using manual entry"
                    if prompt_secret "google-cloud-speech-credentials" "Google Cloud Speech-to-Text service account JSON (paste the entire JSON content)" 2>/dev/null; then
                        log "Google Cloud Speech credentials configured manually"
                    fi
                fi
            ;;
        2)
                if prompt_secret "google-cloud-speech-credentials" "Google Cloud Speech-to-Text service account JSON (paste the entire JSON content)" 2>/dev/null; then
                    log "Google Cloud Speech credentials configured manually"
                fi
            ;;
            *)
                log "Skipping Google Cloud Speech credentials"
                ;;
        esac
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
