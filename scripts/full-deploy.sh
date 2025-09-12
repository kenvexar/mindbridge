#!/bin/bash

# MindBridge 完全自動デプロイスクリプト
# Usage: ./scripts/full-deploy.sh <PROJECT_ID> [--with-optional] [--skip-existing]

set -euo pipefail

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# 引数処理
PROJECT_ID=""
WITH_OPTIONAL=false
SKIP_EXISTING=false

# Parse command line arguments
if [[ " $* " == *" --with-optional "* ]]; then
    WITH_OPTIONAL=true
fi

if [[ " $* " == *" --skip-existing "* ]]; then
    SKIP_EXISTING=true
fi

# Get project ID from arguments (first non-flag argument)
for arg in "$@"; do
    if [[ "$arg" != "--with-optional" && "$arg" != "--skip-existing" ]]; then
        PROJECT_ID="$arg"
        break
    fi
done

if [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}[ERROR]${NC} プロジェクト ID を指定してください"
    echo "使用方法: ./scripts/full-deploy.sh <PROJECT_ID> [--with-optional] [--skip-existing]"
    echo ""
    echo "フラグ:"
    echo "  --with-optional: オプション機能を自動セットアップ"
    echo "  --skip-existing: 既存のシークレットをスキップ"
    echo ""
    echo "例:"
    echo "  ./scripts/full-deploy.sh mindbridge-bot-12345"
    echo "  ./scripts/full-deploy.sh mindbridge-bot-12345 --with-optional"
    echo "  ./scripts/full-deploy.sh mindbridge-bot-12345 --skip-existing --with-optional"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGION="us-central1"

# ログ関数
log_header() {
    echo ""
    echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║ $1${NC}"
    echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# プログレス表示
show_progress() {
    local step=$1
    local total=$2
    local description=$3

    echo -e "${PURPLE}[${step}/${total}]${NC} ${description}"
}

# 前提条件チェック
check_prerequisites() {
    log_step "前提条件をチェック中..."

    # スクリプトファイル存在確認
    local required_scripts=(
        "setup-environment.sh"
        "setup-secrets.sh"
        "generate-speech-credentials.sh"
        "deploy.sh"
    )

    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$SCRIPT_DIR/$script" ]]; then
            log_error "必要なスクリプトが見つかりません: $script"
            exit 1
        fi
    done

    # 実行権限確認・付与
    chmod +x "$SCRIPT_DIR"/*.sh

    log_success "前提条件チェック完了"
}

# 確認メッセージ表示
show_deployment_info() {
    log_header "MindBridge 完全デプロイ"

    echo -e "${CYAN}デプロイ設定:${NC}"
    echo -e "  プロジェクト: ${GREEN}$PROJECT_ID${NC}"
    echo -e "  リージョン:   ${GREEN}$REGION${NC}"
    echo -e "  オプション機能: ${GREEN}$([ "$WITH_OPTIONAL" = true ] && echo "有効" || echo "無効")${NC}"
    echo ""

    echo -e "${CYAN}デプロイ手順:${NC}"
    echo "  1. Google Cloud 環境セットアップ"
    echo "  2. 必須シークレット設定"
    if [[ "$WITH_OPTIONAL" = true ]]; then
        echo "  3. オプション機能設定"
        echo "  4. Cloud Run デプロイ"
    else
        echo "  3. Cloud Run デプロイ"
    fi
    echo ""

    echo -n "続行しますか? (y/n): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "デプロイをキャンセルしました"
        exit 0
    fi
    echo ""
}

# 段階的デプロイ実行
run_deployment_steps() {
    local total_steps=3
    if [[ "$WITH_OPTIONAL" = true ]]; then
        total_steps=4
    fi

    # Step 1: 環境セットアップ
    show_progress 1 $total_steps "Google Cloud 環境をセットアップ中..."
    if ! "$SCRIPT_DIR/setup-environment.sh" "$PROJECT_ID"; then
        log_error "環境セットアップに失敗しました"
        exit 1
    fi
    log_success "環境セットアップ完了"
    echo ""

    # Step 2: 必須シークレット設定
    show_progress 2 $total_steps "必須シークレットを設定中..."
    echo "必要な認証情報を入力してください："
    
    # Build arguments for setup-secrets.sh
    local secrets_args=("$PROJECT_ID")
    if [[ "$WITH_OPTIONAL" = true ]]; then
        secrets_args+=("--with-optional")
    fi
    if [[ "$SKIP_EXISTING" = true ]]; then
        secrets_args+=("--skip-existing")
    fi
    
    if ! "$SCRIPT_DIR/setup-secrets.sh" "${secrets_args[@]}"; then
        log_error "シークレット設定に失敗しました"
        exit 1
    fi
    log_success "必須シークレット設定完了"
    echo ""

    # Step 3: オプション機能設定（条件付き）
    local deploy_step=3
    if [[ "$WITH_OPTIONAL" = true ]]; then
        show_progress 3 $total_steps "オプション機能を設定中..."
        if ! "$SCRIPT_DIR/setup-optional-features.sh" "$PROJECT_ID"; then
            log_error "オプション機能設定に失敗しました"
            exit 1
        fi
        log_success "オプション機能設定完了"
        echo ""
        deploy_step=4
    fi

    # Final Step: デプロイ
    show_progress $deploy_step $total_steps "Cloud Run にデプロイ中..."
    if ! "$SCRIPT_DIR/deploy.sh" "$PROJECT_ID"; then
        log_error "デプロイに失敗しました"
        exit 1
    fi
    log_success "デプロイ完了"
}

# デプロイ後の確認
post_deployment_check() {
    log_step "デプロイ後の確認を実行中..."

    # サービス URL 取得
    local service_url
    service_url=$(gcloud run services describe mindbridge \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='value(status.url)' 2>/dev/null || echo "")

    if [[ -n "$service_url" ]]; then
        echo -e "${GREEN}🌐 サービス URL: $service_url${NC}"

        # ヘルスチェック（非ブロッキング）
        echo -n "ヘルスチェック中..."
        if curl -f -s --max-time 10 "$service_url/health" > /dev/null 2>&1; then
            echo -e " ${GREEN}✅ OK${NC}"
        else
            echo -e " ${YELLOW}⏳ 起動中（数分お待ちください）${NC}"
        fi
    else
        log_warning "サービス URL を取得できませんでした"
    fi
}

# 完了メッセージ
show_completion_message() {
    log_header "🎉 MindBridge デプロイ完了！"

    echo -e "${CYAN}次のステップ:${NC}"
    echo ""
    echo -e "${BOLD}1. Discord Bot の招待${NC}"
    echo "   Bot を個人サーバーに招待してください"
    echo ""
    echo -e "${BOLD}2. Discord チャンネルの準備${NC}"
    echo "   以下 3 つのチャンネルを作成してください："
    echo -e "   • ${GREEN}#memo${NC}         - メイン入力チャンネル"
    echo -e "   • ${GREEN}#notifications${NC} - システム通知"
    echo -e "   • ${GREEN}#commands${NC}      - ボットコマンド"
    echo ""
    echo -e "${BOLD}3. 動作テスト${NC}"
    echo "   #memo チャンネルで「テストメッセージ」を送信"
    echo ""
    echo -e "${CYAN}管理コマンド:${NC}"
    echo "• ログ確認:       gcloud logs tail --service=mindbridge --project=$PROJECT_ID"
    echo "• サービス詳細:   gcloud run services describe mindbridge --region=$REGION --project=$PROJECT_ID"
    echo "• 環境変数更新:   gcloud run services update mindbridge --region=$REGION --project=$PROJECT_ID --set-env-vars KEY=VALUE"
    echo ""

    if [[ "$WITH_OPTIONAL" = true ]]; then
        echo -e "${CYAN}オプション機能:${NC}"
        echo "• 🎤 音声メモ:   Discord に音声ファイルを送信"
        echo "• 💪 健康データ: 初回 OAuth 認証が必要（ログ確認）"
        echo "• 📅 カレンダー: 初回 OAuth 認証が必要（ログ確認）"
        echo ""
    fi

    echo -e "${GREEN}${BOLD}デプロイ完了！ MindBridge をお楽しみください 🚀${NC}"
}

# エラーハンドリング
trap 'log_error "デプロイプロセスが中断されました"; exit 1' ERR

# メイン処理
main() {
    check_prerequisites
    show_deployment_info
    run_deployment_steps
    post_deployment_check
    show_completion_message
}

# 実行
main "$@"
