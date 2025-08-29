#!/bin/bash

# GitHub シークレット設定専用スクリプト
# Usage: ./scripts/setup-github-secrets.sh [PROJECT_ID]

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

main() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  GitHub シークレット設定${NC}"
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
    
    echo -e "${YELLOW}GitHub 関連の設定を行います${NC}"
    echo
    echo "必要な情報:"
    echo "1. GitHub Personal Access Token (repo, workflow 権限が必要)"
    echo "2. Obsidian バックアップ用 GitHub リポジトリ URL"
    echo
    echo -e "${BLUE}GitHub Personal Access Token の作成方法:${NC}"
    echo "1. https://github.com/settings/tokens にアクセス"
    echo "2. 'Generate new token (classic)' をクリック"
    echo "3. トークン名: 'MindBridge Obsidian Sync'"
    echo "4. 権限を選択: repo, workflow"
    echo "5. トークンを生成"
    echo
    echo -e "${BLUE}GitHub リポジトリの作成方法:${NC}"
    echo "1. GitHub で新しいプライベートリポジトリを作成"
    echo "2. リポジトリ名: obsidian-vault (推奨)"
    echo "3. プライベート設定を選択"
    echo
    read -p "準備ができたら Enter を押してください..."
    
    echo
    echo "GitHub Personal Access Token を入力してください:"
    echo "(入力は非表示になります)"
    read -s github_token
    echo
    
    if [[ -z "$github_token" ]]; then
        error "GitHub token が入力されていません"
    fi
    
    echo "Obsidian バックアップリポジトリの URL を入力してください:"
    echo "例: https://github.com/yourusername/obsidian-vault.git"
    read backup_repo
    echo
    
    if [[ -z "$backup_repo" ]]; then
        error "リポジトリ URL が入力されていません"
    fi
    
    # Create or update secrets
    log "GitHub token を設定中..."
    if gcloud secrets describe "github-token" --project="$PROJECT_ID" &>/dev/null; then
        echo -n "$github_token" | gcloud secrets versions add "github-token" \
            --data-file=- --project="$PROJECT_ID"
        log "GitHub token を更新しました"
    else
        echo -n "$github_token" | gcloud secrets create "github-token" \
            --data-file=- --project="$PROJECT_ID"
        log "GitHub token を作成しました"
    fi
    
    log "バックアップリポジトリ URL を設定中..."
    if gcloud secrets describe "obsidian-backup-repo" --project="$PROJECT_ID" &>/dev/null; then
        echo -n "$backup_repo" | gcloud secrets versions add "obsidian-backup-repo" \
            --data-file=- --project="$PROJECT_ID"
        log "バックアップリポジトリ URL を更新しました"
    else
        echo -n "$backup_repo" | gcloud secrets create "obsidian-backup-repo" \
            --data-file=- --project="$PROJECT_ID"
        log "バックアップリポジトリ URL を作成しました"
    fi
    
    # Set up IAM permissions
    log "IAM 権限を設定中..."
    SERVICE_ACCOUNT="mindbridge-service@${PROJECT_ID}.iam.gserviceaccount.com"
    
    for secret in "github-token" "obsidian-backup-repo"; do
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:$SERVICE_ACCOUNT" \
            --role="roles/secretmanager.secretAccessor" \
            --project="$PROJECT_ID" 2>/dev/null || true
    done
    
    echo
    echo -e "${GREEN}✅ GitHub シークレットの設定が完了しました！${NC}"
    echo
    echo "設定されたシークレット:"
    gcloud secrets list --project="$PROJECT_ID" --filter="name:github-token OR name:obsidian-backup-repo" --format="table(name,createTime)"
    echo
    echo "次のステップ:"
    echo "1. ./scripts/deploy.sh でサービスを再デプロイ"
    echo "2. Discord でメモを作成して GitHub 同期をテスト"
}

main "$@"