#!/bin/bash

# MindBridge オプション機能設定スクリプト
# Usage: ./scripts/setup-optional-features.sh [PROJECT_ID]

set -euo pipefail

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

PROJECT_ID=${1:-$(gcloud config get-value project)}

# ログ関数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     MindBridge オプション機能設定      ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "プロジェクト: ${GREEN}$PROJECT_ID${NC}"
echo ""

# セキュアな入力関数
secure_input() {
    local prompt="$1"
    local var_name="$2"
    local hide_input="${3:-true}"

    echo -e "${PURPLE}[INPUT]${NC} $prompt"
    if [[ "$hide_input" == "true" ]]; then
        read -rs value
        echo
    else
        read -r value
    fi

    eval "$var_name='$value'"
}

# シークレット作成関数
create_secret() {
    local secret_name="$1"
    local secret_value="$2"
    local description="$3"

    if [[ -z "$secret_value" ]]; then
        log_warning "❌ $secret_name: 値が空です（スキップ）"
        return 0
    fi

    if gcloud secrets describe "$secret_name" &>/dev/null; then
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
        log_success "✅ $secret_name: 更新完了"
    else
        echo -n "$secret_value" | gcloud secrets create "$secret_name" --data-file=-
        if [[ -n "$description" ]]; then
            # Convert description to valid label format (lowercase, replace spaces with hyphens)
            local label_description=$(echo "$description" | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g' | sed 's/[^a-z0-9_-]//g')
            gcloud secrets update "$secret_name" --update-labels="description=$label_description" 2>/dev/null || true
        fi
        log_success "✅ $secret_name: 作成完了"
    fi
}

# Google Cloud Speech API 設定
setup_speech_api() {
    log_step "🎤 音声メモ機能（ Google Cloud Speech API ）の設定"
    echo ""

    echo -e "${CYAN}Google Cloud Speech API を有効にしますか？${NC}"
    echo "この機能により Discord に送信した音声ファイルが自動で文字起こしされます。"
    echo -n "(y/n): "
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_warning "音声メモ機能をスキップしました"
        return 0
    fi

    # Speech API 有効化
    log_info "Speech API を有効化中..."
    gcloud services enable speech.googleapis.com --quiet

    # サービスアカウント作成（既存チェック）
    SA_SPEECH="mindbridge-speech"
    SA_SPEECH_EMAIL="${SA_SPEECH}@${PROJECT_ID}.iam.gserviceaccount.com"

    if ! gcloud iam service-accounts describe "$SA_SPEECH_EMAIL" &>/dev/null; then
        log_info "音声処理用サービスアカウントを作成中..."
        gcloud iam service-accounts create "$SA_SPEECH" \
            --display-name="MindBridge Speech Service Account" \
            --description="Speech-to-text processing service account"

        # Speech API 権限付与
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$SA_SPEECH_EMAIL" \
            --role="roles/speech.client" --quiet
    fi

    # サービスアカウントキー作成
    KEY_FILE="/tmp/mindbridge-speech-key.json"
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SA_SPEECH_EMAIL"

    # シークレットに保存
    create_secret "google-application-credentials" "$(cat "$KEY_FILE")" "Google Cloud Speech API credentials"

    # 一時ファイル削除
    rm -f "$KEY_FILE"

    log_success "🎤 音声メモ機能設定完了"
}

# Garmin Connect 設定（ python-garminconnect ライブラリ用）
setup_garmin_api() {
    log_step "💪 健康データ統合（ Garmin Connect ）の設定"
    echo ""

    # 既存のシークレットをチェック
    garmin_username_exists=$(gcloud secrets describe "garmin-username" --project="$PROJECT_ID" 2>/dev/null && echo "true" || echo "false")
    garmin_password_exists=$(gcloud secrets describe "garmin-password" --project="$PROJECT_ID" 2>/dev/null && echo "true" || echo "false")

    if [[ "$garmin_username_exists" == "true" && "$garmin_password_exists" == "true" ]]; then
        log_success "✅ Garmin Connect 認証情報は既に設定済みです"
        echo "基本設定（ setup-secrets.sh ）で既に設定されています。"
        echo -e "${GREEN}設定をスキップします。${NC}"
        return 0
    fi

    echo -e "${CYAN}Garmin Connect 認証情報を設定しますか？${NC}"
    echo "この機能により Garmin デバイスの健康データが自動で Obsidian に記録されます。"
    echo ""
    echo -n "(y/n): "
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_warning "Garmin 統合設定をスキップしました"
        return 0
    fi

    echo ""
    echo -e "${CYAN}Garmin Connect 認証について:${NC}"
    echo "• python-garminconnect ライブラリを使用します"
    echo "• OAuth 不要：ユーザー名/パスワード認証方式"
    echo "• Garmin Connect アカウントの認証情報を使用"
    echo ""

    secure_input "Garmin Connect ユーザー名またはメールアドレス:" GARMIN_USERNAME
    secure_input "Garmin Connect パスワード:" GARMIN_PASSWORD

    create_secret "garmin-username" "$GARMIN_USERNAME" "Garmin Connect username"
    create_secret "garmin-password" "$GARMIN_PASSWORD" "Garmin Connect password"

    echo ""
    echo -e "${GREEN}[情報]${NC} 設定完了後、ボットが自動的に健康データを取得します。"
    echo "初回認証時に数分かかる場合があります。"

    log_success "💪 Garmin 統合設定完了"
}

# Google Calendar API 設定
setup_calendar_api() {
    log_step "📅 スケジュール統合（ Google Calendar API ）の設定"
    echo ""

    echo -e "${CYAN}Google Calendar API を設定しますか？${NC}"
    echo "この機能により Discord でスケジュール管理ができるようになります。"
    echo -n "(y/n): "
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_warning "Calendar 統合をスキップしました"
        return 0
    fi

    # Calendar API 有効化
    log_info "Calendar API を有効化中..."
    gcloud services enable calendar-readonly.googleapis.com --quiet

    # 事前チェック: OAuth 同意画面の設定確認
    log_info "OAuth 同意画面の設定を確認中..."
    OAUTH_CONSENT_STATUS=""
    if timeout 10s bash -c "
        CONSENT_STATUS_TEMP=\$(gcloud alpha iap oauth-brands list --format='value(applicationTitle)' 2>&1)
        echo \"\$CONSENT_STATUS_TEMP\" > /tmp/consent_check_$$
    " 2>/dev/null; then
        OAUTH_CONSENT_STATUS=$(cat /tmp/consent_check_$$ 2>/dev/null || echo "")
        rm -f /tmp/consent_check_$$
    else
        rm -f /tmp/consent_check_$$
        log_warning "OAuth 同意画面の確認がタイムアウトしました"
    fi

    echo ""
    echo -e "${CYAN}Google Calendar OAuth 認証情報を自動生成しますか？${NC}"
    echo "1. Auto-generate OAuth credentials (recommended)"
    echo "2. Manually enter credentials.json"

    # OAuth 同意画面が未設定の場合は警告を表示
    if [[ -z "$OAUTH_CONSENT_STATUS" || "$OAUTH_CONSENT_STATUS" == *"ERROR"* ]]; then
        echo ""
        echo -e "${YELLOW}⚠️  注意: OAuth 同意画面が未設定の可能性があります${NC}"
        echo "自動生成に失敗する場合は、以下の手順を実行してください："
        echo "1. Google Cloud Console → APIs & Services → OAuth consent screen"
        echo "2. User Type: External を選択して設定を完了"
    fi

    echo -n "Choose option (1/2): "
    read -r oauth_choice

    if [[ "$oauth_choice" == "1" ]]; then
        log_info "OAuth クライアント ID を自動生成中..."

        # Cloud Run の URL を取得（存在する場合）
        CLOUD_RUN_URL=""
        if gcloud run services describe mindbridge --region=us-central1 --format="value(status.url)" 2>/dev/null; then
            CLOUD_RUN_URL=$(gcloud run services describe mindbridge --region=us-central1 --format="value(status.url)" 2>/dev/null)
        fi

        # リダイレクト URI を準備
        REDIRECT_URIS="http://localhost:8080/oauth/callback"
        if [[ -n "$CLOUD_RUN_URL" ]]; then
            REDIRECT_URIS="$REDIRECT_URIS,$CLOUD_RUN_URL/oauth/callback"
        fi

        # OAuth 設定ファイルを一時的に作成
        OAUTH_CONFIG="/tmp/oauth-config-$$.json"
        cat > "$OAUTH_CONFIG" <<EOF
{
  "displayName": "MindBridge Calendar Integration",
  "webSettings": {
    "authorizedRedirectUris": [
      "http://localhost:8080/oauth/callback"$(if [[ -n "$CLOUD_RUN_URL" ]]; then echo ",\"$CLOUD_RUN_URL/oauth/callback\""; fi)
    ]
  }
}
EOF

        # gcloud を使用して OAuth クライアントを作成（タイムアウト対応）
        log_info "OAuth クライアント ID を作成中..."

        # タイムアウトとエラーハンドリングを追加
        OAUTH_CREATE_SUCCESS=false
        CLIENT_RESULT=""

        # 30 秒タイムアウトで OAuth クライアント作成を試行
        if timeout 30s bash -c "
            CLIENT_RESULT_TEMP=\$(gcloud beta identity oauth-clients create --config-from-file='$OAUTH_CONFIG' --format='value(name)' 2>&1)
            echo \"\$CLIENT_RESULT_TEMP\" > /tmp/oauth_result_$$
        " 2>/dev/null; then
            CLIENT_RESULT=$(cat /tmp/oauth_result_$$ 2>/dev/null || echo "")
            rm -f /tmp/oauth_result_$$

            # 成功判定（ projects/で始まる場合は成功）
            if [[ "$CLIENT_RESULT" == projects/* ]]; then
                CLIENT_ID=$(echo "$CLIENT_RESULT" | cut -d'/' -f4)
                log_success "OAuth クライアント ID が作成されました: $CLIENT_ID"
                OAUTH_CREATE_SUCCESS=true

                # クライアントシークレットを取得（タイムアウト付き）
                CLIENT_SECRET=""
                if timeout 15s bash -c "
                    SECRET_TEMP=\$(gcloud beta identity oauth-clients describe '$CLIENT_RESULT' --format='value(secret)' 2>&1)
                    echo \"\$SECRET_TEMP\" > /tmp/oauth_secret_$$
                " 2>/dev/null; then
                    CLIENT_SECRET=$(cat /tmp/oauth_secret_$$ 2>/dev/null || echo "")
                    rm -f /tmp/oauth_secret_$$
                fi

                if [[ -z "$CLIENT_SECRET" ]]; then
                    log_warning "クライアントシークレットの取得に失敗しました"
                    CLIENT_SECRET="<MANUAL_SETUP_REQUIRED>"
                fi

                # credentials.json 形式で生成
                CALENDAR_CREDENTIALS=$(cat <<EOF
{
  "web": {
    "client_id": "$CLIENT_ID",
    "client_secret": "$CLIENT_SECRET",
    "project_id": "$PROJECT_ID",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "redirect_uris": [$(echo "$REDIRECT_URIS" | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/')],
    "javascript_origins": ["http://localhost:8080"$(if [[ -n "$CLOUD_RUN_URL" ]]; then echo ",\"$CLOUD_RUN_URL\""; fi)]
  }
}
EOF
)
            else
                log_warning "OAuth クライアント作成が不正な応答を返しました: $CLIENT_RESULT"
            fi
        else
            # タイムアウトまたはコマンドエラー
            CLIENT_RESULT=$(cat /tmp/oauth_result_$$ 2>/dev/null || echo "timeout or command failed")
            rm -f /tmp/oauth_result_$$
            log_warning "OAuth クライアント作成がタイムアウトまたは失敗しました: $CLIENT_RESULT"
        fi

        # 設定ファイルをクリーンアップ
        rm -f "$OAUTH_CONFIG"

        # 自動生成に失敗した場合は手動設定にフォールバック
        if [[ "$OAUTH_CREATE_SUCCESS" != "true" ]]; then
            log_warning "自動生成に失敗しました。手動設定に切り替えます..."
            oauth_choice="2"
        fi
    fi

    if [[ "$oauth_choice" == "2" ]]; then
        echo ""
        echo -e "${CYAN}Google Calendar API OAuth 設定手順:${NC}"
        echo "1. Google Cloud Console → APIs & Services → Credentials"
        echo "2. 'Create Credentials' → 'OAuth client ID'"
        echo "3. Application type: 'Web application'"
        echo "4. Name: 'MindBridge Calendar Integration'"
        echo "5. Authorized redirect URIs に以下を追加:"
        echo "   - http://localhost:8080/oauth/callback"
        if [[ -n "$CLOUD_RUN_URL" ]]; then
            echo "   - $CLOUD_RUN_URL/oauth/callback"
        else
            echo "   - https://YOUR-CLOUD-RUN-URL/oauth/callback"
        fi
        echo "6. credentials.json をダウンロード"
        echo ""

        echo -e "${PURPLE}[INPUT]${NC} credentials.json の内容をペーストしてください（ Ctrl+D で終了）:"
        CALENDAR_CREDENTIALS=$(cat)
    fi

    if [[ -n "$CALENDAR_CREDENTIALS" ]]; then
        create_secret "google-calendar-credentials" "$CALENDAR_CREDENTIALS" "Google Calendar OAuth credentials"
        log_success "📅 Calendar 統合設定完了"
    else
        log_warning "Calendar 認証情報が空です（スキップ）"
    fi
}

# Webhook 設定
setup_webhooks() {
    log_step "🔔 通知 Webhook の設定"
    echo ""

    echo -e "${CYAN}外部 Webhook 通知を設定しますか？${NC}"
    echo "Slack や Discord の追加チャンネルに通知を送信できます。"
    echo -n "(y/n): "
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_warning "Webhook 設定をスキップしました"
        return 0
    fi

    echo ""
    echo -e "${CYAN}Slack Webhook URL （空白でスキップ）:${NC}"
    secure_input "Slack Webhook URL:" SLACK_WEBHOOK false

    echo -e "${CYAN}Discord Webhook URL （空白でスキップ）:${NC}"
    secure_input "Discord Webhook URL:" DISCORD_WEBHOOK false

    if [[ -n "$SLACK_WEBHOOK" ]]; then
        create_secret "slack-webhook-url" "$SLACK_WEBHOOK" "Slack notification webhook URL"
    fi

    if [[ -n "$DISCORD_WEBHOOK" ]]; then
        create_secret "discord-webhook-url" "$DISCORD_WEBHOOK" "Discord notification webhook URL"
    fi

    log_success "🔔 Webhook 設定完了"
}

# その他の設定
setup_additional_settings() {
    log_step "⚙️  その他の設定"
    echo ""

    # 管理者ユーザー ID
    echo -e "${CYAN}管理者 Discord User ID （空白でスキップ）:${NC}"
    echo "管理者コマンドを使用できるユーザーを指定します。"
    secure_input "Discord User ID:" ADMIN_USER_ID false

    if [[ -n "$ADMIN_USER_ID" ]]; then
        create_secret "admin-user-id" "$ADMIN_USER_ID" "Discord admin user ID"
    fi

    # タイムゾーン
    echo -e "${CYAN}タイムゾーン設定（デフォルト: Asia/Tokyo ）:${NC}"
    secure_input "タイムゾーン:" TIMEZONE false
    TIMEZONE=${TIMEZONE:-Asia/Tokyo}

    create_secret "timezone" "$TIMEZONE" "Application timezone"

    log_success "⚙️  追加設定完了"
}

# 設定確認と完了メッセージ
show_completion() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║      オプション機能設定完了！         ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${CYAN}設定されたシークレット一覧:${NC}"
    gcloud secrets list --format="table(name,createTime.date(format='%Y-%m-%d %H:%M'))" --sort-by="createTime"

    echo ""
    echo -e "${CYAN}次のステップ:${NC}"
    echo -e "1. 環境変数設定: Cloud Run サービスでオプション機能を有効化"
    echo -e "2. デプロイ実行:  ${YELLOW}./scripts/deploy.sh${NC}"
    echo -e "3. 動作確認:      各機能のテストを実行"
    echo ""
    echo -e "${CYAN}機能別有効化コマンド:${NC}"
    echo "gcloud run services update mindbridge \\"
    echo "  --region=us-central1 \\"
    echo "  --set-env-vars=\"ENABLE_SPEECH_PROCESSING=true,ENABLE_GARMIN_INTEGRATION=true,ENABLE_CALENDAR_INTEGRATION=true\""
    echo ""
}

# メイン処理
main() {
    setup_speech_api
    echo ""
    setup_garmin_api
    echo ""
    setup_calendar_api
    echo ""
    setup_webhooks
    echo ""
    setup_additional_settings
    show_completion
}

# 実行
main "$@"
