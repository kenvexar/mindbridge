#!/bin/bash

# MindBridge Google Cloud Speech-to-Text 認証情報生成スクリプト
# Usage: ./scripts/generate-speech-credentials.sh <PROJECT_ID>

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

# 引数処理
PROJECT_ID=${1:-}
JSON_ONLY=${2:-false}

if [[ -z "$PROJECT_ID" ]]; then
    log_error "プロジェクト ID を指定してください"
    echo "使用方法: ./scripts/generate-speech-credentials.sh <PROJECT_ID> [json-only]"
    echo "例: ./scripts/generate-speech-credentials.sh mindbridge-471813"
    echo "   ./scripts/generate-speech-credentials.sh mindbridge-471813 json-only"
    exit 1
fi

SA_NAME="mindbridge-speech"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="/tmp/mindbridge-speech-credentials-$$.json"

# json-only モードではヘッダーを表示しない
if [[ "$JSON_ONLY" != "json-only" ]]; then
    echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Speech-to-Text 認証情報生成          ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "プロジェクト: ${GREEN}$PROJECT_ID${NC}"
    echo -e "サービスアカウント: ${GREEN}$SA_EMAIL${NC}"
    echo ""
fi

# 前提条件チェック
check_prerequisites() {
    if [[ "$JSON_ONLY" != "json-only" ]]; then
        log_step "前提条件をチェック中..."
    fi

    # gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI がインストールされていません"
        exit 1
    fi

    # 認証確認
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 &> /dev/null; then
        log_error "gcloud で認証されていません"
        echo "実行してください: gcloud auth login"
        exit 1
    fi

    # プロジェクト設定
    if [[ "$JSON_ONLY" == "json-only" ]]; then
        gcloud config set project "$PROJECT_ID" --quiet >/dev/null 2>&1
    else
        gcloud config set project "$PROJECT_ID" --quiet
    fi

    if [[ "$JSON_ONLY" != "json-only" ]]; then
        log_success "前提条件チェック完了"
    fi
}

# サービスアカウント確認・作成
setup_service_account() {
    if [[ "$JSON_ONLY" != "json-only" ]]; then
        log_step "サービスアカウントを確認中..."
    fi

    if ! gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
        if [[ "$JSON_ONLY" != "json-only" ]]; then
            log_info "Speech サービスアカウントが存在しません。作成中..."
        fi

        if [[ "$JSON_ONLY" == "json-only" ]]; then
            gcloud iam service-accounts create "$SA_NAME" \
                --display-name="MindBridge Speech Service Account" \
                --description="Service account for speech-to-text operations" >/dev/null 2>&1

            # 権限付与
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:$SA_EMAIL" \
                --role="roles/speech.client" --quiet >/dev/null 2>&1
        else
            gcloud iam service-accounts create "$SA_NAME" \
                --display-name="MindBridge Speech Service Account" \
                --description="Service account for speech-to-text operations"

            # 権限付与
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:$SA_EMAIL" \
                --role="roles/speech.client" --quiet
        fi

        if [[ "$JSON_ONLY" != "json-only" ]]; then
            log_success "サービスアカウント作成完了"
        fi
    else
        if [[ "$JSON_ONLY" != "json-only" ]]; then
            log_info "サービスアカウントは既に存在します"
        fi
    fi
}

# 認証情報キー生成
generate_credentials() {
    if [[ "$JSON_ONLY" != "json-only" ]]; then
        log_step "認証情報キーを生成中..."
    fi

    # 既存のキーを確認
    local existing_keys
    if [[ "$JSON_ONLY" == "json-only" ]]; then
        existing_keys=$(gcloud iam service-accounts keys list \
            --iam-account="$SA_EMAIL" \
            --format="value(name)" \
            --filter="keyType:USER_MANAGED" 2>/dev/null || echo "")
    else
        existing_keys=$(gcloud iam service-accounts keys list \
            --iam-account="$SA_EMAIL" \
            --format="value(name)" \
            --filter="keyType:USER_MANAGED" 2>/dev/null || echo "")
    fi

    if [[ -n "$existing_keys" ]]; then
        if [[ "$JSON_ONLY" != "json-only" ]]; then
            log_warning "既存のユーザー管理キーが見つかりました"
            echo "既存のキーを削除して新しいキーを作成しますか? (y/n): "
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                # 既存キーを削除
                while IFS= read -r key_name; do
                    if [[ -n "$key_name" ]]; then
                        log_info "既存キーを削除中: $(basename "$key_name")"
                        gcloud iam service-accounts keys delete "$(basename "$key_name")" \
                            --iam-account="$SA_EMAIL" --quiet >/dev/null 2>&1
                    fi
                done <<< "$existing_keys"
            fi
        else
            # JSON-only モードでは自動的に既存キーを削除
            while IFS= read -r key_name; do
                if [[ -n "$key_name" ]]; then
                    gcloud iam service-accounts keys delete "$(basename "$key_name")" \
                        --iam-account="$SA_EMAIL" --quiet >/dev/null 2>&1
                fi
            done <<< "$existing_keys"
        fi
    fi

    # 新しいキーを生成
    if [[ "$JSON_ONLY" == "json-only" ]]; then
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account="$SA_EMAIL" >/dev/null 2>&1
    else
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account="$SA_EMAIL"
    fi

    if [[ "$JSON_ONLY" != "json-only" ]]; then
        log_success "認証情報キー生成完了"
    fi
}

# 認証情報表示
display_credentials() {
    if [[ "$JSON_ONLY" == "json-only" ]]; then
        # JSON のみモード: マーカー付きで JSON のみ出力
        echo "--- JSON 開始 ---"
        cat "$KEY_FILE"
        echo "--- JSON 終了 ---"
    else
        # 通常モード: 詳細表示
        log_step "認証情報を表示中..."

        echo ""
        echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║           生成された JSON             ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}以下の JSON 全体をコピーしてください:${NC}"
        echo ""
        echo -e "${CYAN}--- JSON 開始 ---${NC}"
        cat "$KEY_FILE"
        echo ""
        echo -e "${CYAN}--- JSON 終了 ---${NC}"
        echo ""
    fi
}

# 清理処理
cleanup() {
    if [[ "$JSON_ONLY" != "json-only" ]]; then
        log_step "一時ファイルを清理中..."
    fi

    if [[ -f "$KEY_FILE" ]]; then
        rm -f "$KEY_FILE"
        if [[ "$JSON_ONLY" != "json-only" ]]; then
            log_success "一時ファイルを削除しました"
        fi
    fi
}

# 使用方法表示
show_usage_instructions() {
    # JSON-only モードでは使用方法を表示しない
    if [[ "$JSON_ONLY" == "json-only" ]]; then
        return 0
    fi

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║             使用方法                  ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}1. セットアップスクリプトで使用:${NC}"
    echo "   デプロイ中のプロンプトで上記 JSON 全体を貼り付け"
    echo ""
    echo -e "${CYAN}2. 手動設定の場合:${NC}"
    echo "   環境変数 GOOGLE_APPLICATION_CREDENTIALS に JSON ファイルパスを設定"
    echo ""
    echo -e "${CYAN}3. セキュリティ注意事項:${NC}"
    echo -e "   • この JSON は ${RED}極秘情報${NC} です"
    echo -e "   • ${RED}GitHub や公開場所には保存しないでください${NC}"
    echo -e "   • 不要になったら必ず削除してください"
    echo ""
}

# エラーハンドリング
trap cleanup EXIT

# メイン処理
main() {
    check_prerequisites
    setup_service_account
    generate_credentials
    display_credentials
    show_usage_instructions
}

# 実行
main "$@"
