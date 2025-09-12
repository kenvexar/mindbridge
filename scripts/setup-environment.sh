#!/bin/bash

# MindBridge Google Cloud 環境セットアップスクリプト
# Usage: ./scripts/setup-environment.sh <PROJECT_ID>

set -euo pipefail

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# プロジェクト ID 確認
PROJECT_ID=${1:-}
if [[ -z "$PROJECT_ID" ]]; then
    log_error "プロジェクト ID を指定してください: ./setup-environment.sh <PROJECT_ID>"
    echo "例: ./setup-environment.sh mindbridge-bot-12345"
    exit 1
fi

REGION="us-central1"

echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     MindBridge 環境セットアップ       ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "プロジェクト: ${GREEN}$PROJECT_ID${NC}"
echo -e "リージョン:   ${GREEN}$REGION${NC}"
echo ""

# 前提条件チェック
check_prerequisites() {
    log_step "前提条件をチェック中..."

    # gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI がインストールされていません"
        echo "インストール: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # 認証確認
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 &> /dev/null; then
        log_error "gcloud で認証されていません"
        echo "実行してください: gcloud auth login"
        exit 1
    fi

    log_success "前提条件チェック完了"
}

# プロジェクト設定
setup_project() {
    log_step "Google Cloud プロジェクトを設定中..."

    # プロジェクト存在確認
    if ! gcloud projects describe "$PROJECT_ID" &>/dev/null; then
        log_error "プロジェクト '$PROJECT_ID' が見つかりません"
        echo "新しいプロジェクトを作成しますか? (y/n): "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            create_project
        else
            exit 1
        fi
    fi

    # プロジェクト設定
    gcloud config set project "$PROJECT_ID"
    log_success "プロジェクト '$PROJECT_ID' に設定完了"
}

# プロジェクト作成
create_project() {
    log_step "新しいプロジェクトを作成中..."

    gcloud projects create "$PROJECT_ID" --name="MindBridge Personal Bot"

    # 課金アカウント確認
    log_info "課金アカウントのリンクが必要です"
    gcloud billing projects link "$PROJECT_ID"

    log_success "プロジェクト '$PROJECT_ID' 作成完了"
}

# API 有効化
enable_apis() {
    log_step "必要な API を有効化中..."

    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "secretmanager.googleapis.com"
        "speech.googleapis.com"
        "iam.googleapis.com"
        "cloudresourcemanager.googleapis.com"
    )

    for api in "${apis[@]}"; do
        log_info "有効化中: $api"
        gcloud services enable "$api" --quiet
    done

    log_success "API 有効化完了"
}

# サービスアカウント作成
create_service_accounts() {
    log_step "サービスアカウントを作成中..."

    # メインサービスアカウント
    local SA_MAIN="mindbridge-service"
    local SA_MAIN_EMAIL="${SA_MAIN}@${PROJECT_ID}.iam.gserviceaccount.com"

    if ! gcloud iam service-accounts describe "$SA_MAIN_EMAIL" &>/dev/null; then
        gcloud iam service-accounts create "$SA_MAIN" \
            --display-name="MindBridge Main Service Account" \
            --description="Main service account for MindBridge bot operations"
        log_success "メインサービスアカウント作成完了"
    else
        log_info "メインサービスアカウントは既に存在します"
    fi

    # 権限付与
    log_info "権限を付与中..."
    local roles=(
        "roles/secretmanager.secretAccessor"
        "roles/logging.logWriter"
        "roles/monitoring.metricWriter"
        "roles/cloudtrace.agent"
    )

    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$SA_MAIN_EMAIL" \
            --role="$role" --quiet
    done

    # Speech API 用サービスアカウント（オプション機能用）
    local SA_SPEECH="mindbridge-speech"
    local SA_SPEECH_EMAIL="${SA_SPEECH}@${PROJECT_ID}.iam.gserviceaccount.com"

    if ! gcloud iam service-accounts describe "$SA_SPEECH_EMAIL" &>/dev/null; then
        gcloud iam service-accounts create "$SA_SPEECH" \
            --display-name="MindBridge Speech Service Account" \
            --description="Service account for speech-to-text operations"

        # サービスアカウント作成の完了を待つ
        log_info "サービスアカウントの作成完了を待機中..."
        sleep 10

        # IAM ポリシーの設定（リトライ機能付き）
        local max_retries=3
        local retry_count=0
        while [ $retry_count -lt $max_retries ]; do
            if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:$SA_SPEECH_EMAIL" \
                --role="roles/speech.client" --quiet; then
                break
            else
                retry_count=$((retry_count + 1))
                if [ $retry_count -lt $max_retries ]; then
                    log_info "IAM ポリシー設定失敗、リトライ中... ($retry_count/$max_retries)"
                    sleep 5
                else
                    log_warning "Speech API 権限の設定に失敗しましたが、継続します"
                fi
            fi
        done

        log_success "Speech API サービスアカウント作成完了"
    else
        log_info "Speech API サービスアカウントは既に存在します"
    fi

    log_success "サービスアカウント設定完了"
}

# Cloud Run 用の設定
setup_cloud_run() {
    log_step "Cloud Run 環境を設定中..."

    # Cloud Run サービスアカウントの権限確認
    local DEFAULT_SA="$PROJECT_ID@appspot.gserviceaccount.com"

    # Artifact Registry リポジトリ作成（必要に応じて）
    if ! gcloud artifacts repositories describe mindbridge-repo \
        --location="$REGION" &>/dev/null; then

        log_info "Artifact Registry リポジトリを作成中..."
        gcloud artifacts repositories create mindbridge-repo \
            --repository-format=docker \
            --location="$REGION" \
            --description="MindBridge Docker images repository"
    fi

    log_success "Cloud Run 環境設定完了"
}

# 設定完了メッセージ
show_completion_message() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║        環境設定完了！                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}次のステップ:${NC}"
    echo -e "1. シークレット設定: ${YELLOW}./scripts/setup-secrets.sh${NC}"
    echo -e "2. デプロイ実行:     ${YELLOW}./scripts/deploy.sh $PROJECT_ID${NC}"
    echo ""
    echo -e "${CYAN}確認コマンド:${NC}"
    echo -e "• プロジェクト確認:   gcloud config get-value project"
    echo -e "• API 確認:           gcloud services list --enabled"
    echo -e "• サービスアカウント: gcloud iam service-accounts list"
    echo ""
}

# メイン処理
main() {
    check_prerequisites
    setup_project
    enable_apis
    create_service_accounts
    setup_cloud_run
    show_completion_message
}

# 実行
main "$@"
