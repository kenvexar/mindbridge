#!/usr/bin/env bash
set -Eeuo pipefail

# MindBridge 統合 CLI（サブコマンドで操作を集約）
# 使い方:
#   ./scripts/manage.sh help
#   ./scripts/manage.sh env <PROJECT_ID>
#   ./scripts/manage.sh secrets <PROJECT_ID> [--with-optional] [--skip-existing]
#   ./scripts/manage.sh optional <PROJECT_ID>
#   ./scripts/manage.sh deploy <PROJECT_ID> [REGION]
#   ./scripts/manage.sh full-deploy <PROJECT_ID> [--with-optional] [--skip-existing]
#   ./scripts/manage.sh ar-clean <PROJECT_ID> [REGION] [REPO] [IMAGE] [KEEP] [OLDER_DAYS] [--no-dry-run]
#   ./scripts/manage.sh run            # ローカル実行（.env 必須）

# ===== 共通ユーティリティ（common.sh を内蔵） =====
if [[ -t 1 ]]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

log__base() {
  # $1: colored tag, remaining: message tokens
  local tag=$1; shift || true
  if (($#)); then
    printf "%b " "$tag"
    printf "%s" "$1"; shift || true
    while (($#)); do printf " %s" "$1"; shift; done
    printf "\n"
  else
    printf "%b\n" "$tag"
  fi
}
log()         { log__base "${GREEN}[INFO]${NC}" "$@"; }
warn()        { log__base "${YELLOW}[WARN]${NC}" "$@"; }
log_step()    { log__base "${CYAN}[STEP]${NC}" "$@"; }
log_success() { log__base "${GREEN}[SUCCESS]${NC}" "$@"; }
log_error()   { log__base "${RED}[ERROR]${NC}" "$@" >&2; }
die()         { log_error "$@"; exit 1; }

require_cmd(){
  local missing=()
  for c in "$@"; do command -v "$c" >/dev/null 2>&1 || missing+=("$c"); done
  (( ${#missing[@]} )) && die "必要なコマンドが見つかりません: ${missing[*]}"
}

ensure_repo_root(){
  local root_dir
  root_dir=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
  cd "$root_dir" || die "リポジトリルートへ移動できません"
}
ensure_gcloud_auth(){ require_cmd gcloud; gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1 >/dev/null 2>&1 || die "gcloud 未認証。'gcloud auth login' を実行してください"; }
ensure_project_id(){
  if [[ -z "${PROJECT_ID:-}" ]]; then PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true); fi
  [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID が未設定です。引数または 'gcloud config set project' で指定してください"
}

confirm(){ local msg=${1:-"続行しますか?"}; read -r -p "$msg [y/N] " yn; [[ "$yn" =~ ^[Yy]$ ]]; }

ensure_repo_root

usage() {
  cat <<USAGE
MindBridge CLI

サブコマンド:
  env <PROJECT_ID>                 Google Cloud 環境セットアップ
  secrets <PROJECT_ID> [FLAGS]     必須/オプションシークレット設定
  optional <PROJECT_ID>            カレンダー/ウェブフック/タイムゾーン設定
  deploy <PROJECT_ID> [REGION]     Cloud Run デプロイ
  full-deploy <PROJECT_ID> [FLAGS] 環境→シークレット→（任意）→デプロイ一括
  ar-clean <PROJECT_ID> [...]      Artifact Registry の古いイメージ削除
  init                             ローカル初期設定（.env 生成）
  run                              ローカル起動（uv 使用）
  help                             このヘルプ

例:
  ./scripts/manage.sh env my-proj
  ./scripts/manage.sh secrets my-proj --with-optional --skip-existing
  ./scripts/manage.sh deploy my-proj us-central1
  ./scripts/manage.sh full-deploy my-proj --with-optional
  ./scripts/manage.sh run
USAGE
}

# ===== env（旧 setup-environment.sh） =====
cmd_env(){
  PROJECT_ID=${1:-}; [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID を指定してください";
  ensure_gcloud_auth
  log_step "プロジェクト存在確認と選択"
  if ! gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    warn "プロジェクト '$PROJECT_ID' が存在しません"
    confirm "新規作成しますか?" || die "中止しました"
    gcloud projects create "$PROJECT_ID" --name="MindBridge Personal Bot"
    log "課金アカウントのリンクを実行します"
    gcloud billing projects link "$PROJECT_ID"
  fi
  gcloud config set project "$PROJECT_ID" --quiet

  log_step "必要 API を有効化"
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com speech.googleapis.com iam.googleapis.com cloudresourcemanager.googleapis.com --quiet

  log_step "サービスアカウント作成/権限付与"
  local SA_MAIN="mindbridge-service"
  local SA_MAIN_EMAIL="${SA_MAIN}@${PROJECT_ID}.iam.gserviceaccount.com"
  gcloud iam service-accounts describe "$SA_MAIN_EMAIL" &>/dev/null || \
    gcloud iam service-accounts create "$SA_MAIN" --display-name="MindBridge Main Service Account"
  for role in roles/secretmanager.secretAccessor roles/logging.logWriter roles/monitoring.metricWriter roles/cloudtrace.agent; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA_MAIN_EMAIL" --role="$role" --quiet >/dev/null 2>&1 || true
  done

  log_step "Artifact Registry リポジトリ確認"
  local REGION=${REGION:-us-central1}
  gcloud artifacts repositories describe mindbridge --location="$REGION" >/dev/null 2>&1 || \
    gcloud artifacts repositories create mindbridge --repository-format=docker --location="$REGION" --description="MindBridge container images"

  log_success "環境セットアップ完了"
  printf "%s\n" "次のステップ: ${YELLOW}./scripts/manage.sh secrets $PROJECT_ID${NC} でシークレットを設定"
}

# ===== secrets（旧 setup-secrets.sh + Speech 自動生成） =====
prompt_secret(){
  local secret_name=$1 desc=$2
  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
    warn "Secret '$secret_name' は既に存在します"
    [[ "$SKIP_EXISTING" == true ]] && { log "--skip-existing によりスキップ"; return 0; }
    confirm "更新しますか?" || { log "スキップ: $secret_name"; return 0; }
  else
    log "作成: $secret_name"
  fi
  echo "説明: $desc"
  read -rs -p "値を入力（入力は表示されません）: " secret_value; echo
  [[ -z "$secret_value" ]] && { warn "空入力。スキップ"; return 1; }
  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
    echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --project="$PROJECT_ID" --data-file=-
  else
    echo -n "$secret_value" | gcloud secrets create "$secret_name" --project="$PROJECT_ID" --data-file=-
  fi
  log_success "$secret_name 設定完了"
}

generate_speech_credentials(){
  local SA_NAME="mindbridge-speech"
  local SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
  local KEY_FILE="/tmp/mb-speech-$$.json"
  gcloud services enable speech.googleapis.com --quiet
  gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null || \
    gcloud iam service-accounts create "$SA_NAME" --display-name="MindBridge Speech Service Account"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA_EMAIL" --role="roles/speech.client" --quiet >/dev/null 2>&1 || true
  gcloud iam service-accounts keys create "$KEY_FILE" --iam-account="$SA_EMAIL"
  local json; json=$(cat "$KEY_FILE"); rm -f "$KEY_FILE"
  if gcloud secrets describe google-cloud-speech-credentials --project="$PROJECT_ID" &>/dev/null; then
    printf %s "$json" | gcloud secrets versions add google-cloud-speech-credentials --project="$PROJECT_ID" --data-file=-
  else
    printf %s "$json" | gcloud secrets create google-cloud-speech-credentials --project="$PROJECT_ID" --data-file=-
  fi
  log_success "google-cloud-speech-credentials を設定しました"
}

cmd_secrets(){
  PROJECT_ID=${1:-}; shift || true
  [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID を指定してください"
  ensure_gcloud_auth; ensure_project_id
  SKIP_EXISTING=false; WITH_OPTIONAL=false
  [[ " $* " == *" --skip-existing "* ]] && SKIP_EXISTING=true
  [[ " $* " == *" --with-optional "* ]] && WITH_OPTIONAL=true

  gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"
  log_step "必須シークレットを設定"
  prompt_secret discord-bot-token "Discord Bot Token"
  prompt_secret discord-guild-id "Discord Guild ID (Server ID)"
  prompt_secret gemini-api-key "Google Gemini API Key"
  prompt_secret github-token "GitHub Personal Access Token (repo)"
  prompt_secret obsidian-backup-repo "GitHub repo URL for Obsidian backup"

  if [[ "$WITH_OPTIONAL" == true ]]; then
    log_step "オプション（Garmin/Speech）"
    prompt_secret garmin-username "Garmin Connect ユーザー名/メール"
    prompt_secret garmin-password "Garmin Connect パスワード"
    if gcloud secrets describe google-cloud-speech-credentials --project="$PROJECT_ID" &>/dev/null; then
      warn "Speech 認証情報は既に存在します（必要なら手動更新してください）"
    else
      confirm "Speech-to-Text 認証情報を自動生成しますか?" && generate_speech_credentials || log "Speech はスキップ"
    fi
  fi

  log_step "サービスアカウントへのアクセス許可付与"
  local SA_MAIN_EMAIL="mindbridge-service@${PROJECT_ID}.iam.gserviceaccount.com"
  for s in discord-bot-token discord-guild-id gemini-api-key garmin-username garmin-password github-token obsidian-backup-repo google-cloud-speech-credentials; do
    gcloud secrets describe "$s" --project="$PROJECT_ID" &>/dev/null || continue
    gcloud secrets add-iam-policy-binding "$s" --member="serviceAccount:$SA_MAIN_EMAIL" --role="roles/secretmanager.secretAccessor" --project="$PROJECT_ID" 2>/dev/null || true
  done
  log_success "Secrets setup 完了"
}

# ===== optional（旧 setup-optional-features.sh の要点） =====
cmd_optional(){
  PROJECT_ID=${1:-}; [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID を指定してください";
  ensure_gcloud_auth; ensure_project_id

  log_step "Google Calendar OAuth credentials（手動または既存を貼り付け）"
  printf "%b\n" "${YELLOW}ブラウザで作成した credentials.json を貼り付け（Enterのみでスキップ）:${NC}"
  printf "%s\n" "手順: Console → APIs & Services → Credentials → OAuth client ID (Web)"
  printf "%s\n" "Redirect URIs: http://localhost:8080/oauth/callback, <Cloud Run URL>/oauth/callback"
  read -r -p "貼り付け開始（Enter でスキップ）: " __dummy || true
  CAL_JSON=$(cat || true)
  if [[ -n "$CAL_JSON" ]]; then
    if gcloud secrets describe google-calendar-credentials --project="$PROJECT_ID" &>/dev/null; then
      printf %s "$CAL_JSON" | gcloud secrets versions add google-calendar-credentials --project="$PROJECT_ID" --data-file=-
    else
      printf %s "$CAL_JSON" | gcloud secrets create google-calendar-credentials --project="$PROJECT_ID" --data-file=-
    fi
    log_success "google-calendar-credentials を保存しました"
  else
    warn "Calendar 認証情報はスキップされました"
  fi

  log_step "Webhook（任意）"
  read -r -p "Slack Webhook URL（空でスキップ）: " SLACK_WEBHOOK || true
  read -r -p "Discord Webhook URL（空でスキップ）: " DISCORD_WEBHOOK || true
  if [[ -n "$SLACK_WEBHOOK" ]]; then
    if gcloud secrets describe slack-webhook-url --project="$PROJECT_ID" &>/dev/null; then
      printf %s "$SLACK_WEBHOOK" | gcloud secrets versions add slack-webhook-url --project="$PROJECT_ID" --data-file=-
    else
      printf %s "$SLACK_WEBHOOK" | gcloud secrets create slack-webhook-url --project="$PROJECT_ID" --data-file=-
    fi
  fi
  if [[ -n "$DISCORD_WEBHOOK" ]]; then
    if gcloud secrets describe discord-webhook-url --project="$PROJECT_ID" &>/dev/null; then
      printf %s "$DISCORD_WEBHOOK" | gcloud secrets versions add discord-webhook-url --project="$PROJECT_ID" --data-file=-
    else
      printf %s "$DISCORD_WEBHOOK" | gcloud secrets create discord-webhook-url --project="$PROJECT_ID" --data-file=-
    fi
  fi

  log_step "管理者/タイムゾーン（任意）"
  read -r -p "管理者 Discord User ID（空でスキップ）: " ADMIN_USER_ID || true
  read -r -p "タイムゾーン [Asia/Tokyo]: " TIMEZONE || true; TIMEZONE=${TIMEZONE:-Asia/Tokyo}
  if [[ -n "$ADMIN_USER_ID" ]]; then
    if gcloud secrets describe admin-user-id --project="$PROJECT_ID" &>/dev/null; then
      printf %s "$ADMIN_USER_ID" | gcloud secrets versions add admin-user-id --project="$PROJECT_ID" --data-file=-
    else
      printf %s "$ADMIN_USER_ID" | gcloud secrets create admin-user-id --project="$PROJECT_ID" --data-file=-
    fi
  fi
  if gcloud secrets describe timezone --project="$PROJECT_ID" &>/dev/null; then
    printf %s "$TIMEZONE" | gcloud secrets versions add timezone --project="$PROJECT_ID" --data-file=-
  else
    printf %s "$TIMEZONE" | gcloud secrets create timezone --project="$PROJECT_ID" --data-file=-
  fi

  log_success "Optional 設定完了"
}

# ===== deploy（旧 deploy.sh の要点） =====
cmd_deploy(){
  PROJECT_ID=${1:-}; REGION=${2:-us-central1}
  [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID を指定してください";
  ensure_gcloud_auth; ensure_project_id
  local SERVICE_NAME=mindbridge IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/mindbridge/mindbridge"
  log_step "必要 API を有効化"
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com --project="$PROJECT_ID" --quiet
  log_step "Artifact Registry リポジトリ確認"
  gcloud artifacts repositories describe mindbridge --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1 || \
    gcloud artifacts repositories create mindbridge --repository-format=docker --location="$REGION" --project="$PROJECT_ID"

  log_step "Cloud Build によるビルド/デプロイ"
  local CB_CONFIG="deploy/cloudbuild.yaml"; [[ -f "$CB_CONFIG" ]] || die "deploy/cloudbuild.yaml が見つかりません"
  local BUILD_ID; BUILD_ID=$(gcloud builds submit --config "$CB_CONFIG" --project="$PROJECT_ID" --format='value(id)') || die "Cloud Build 失敗"
  log_success "Cloud Build 完了 (Build ID: $BUILD_ID)"

  log_step "Cloud Run へ反映"
  local CR_CONFIG="deploy/cloud-run.yaml"; [[ -f "$CR_CONFIG" ]] || die "deploy/cloud-run.yaml が見つかりません"
  if grep -q "PROJECT_ID" "$CR_CONFIG"; then sed "s/PROJECT_ID/$PROJECT_ID/g" "$CR_CONFIG" > /tmp/cloud-run-deploy.yaml; else cp "$CR_CONFIG" /tmp/cloud-run-deploy.yaml; fi
  gcloud run services replace /tmp/cloud-run-deploy.yaml --region="$REGION" --project="$PROJECT_ID"
  local GIT_SHA; GIT_SHA=$(git rev-parse --short HEAD || echo latest)
  gcloud run services update "$SERVICE_NAME" --image="${IMAGE_NAME}:${GIT_SHA}" --region="$REGION" --project="$PROJECT_ID" || true
  rm -f /tmp/cloud-run-deploy.yaml

  log_step "Health Check"
  local URL; URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')
  [[ -n "$URL" ]] && printf "%s\n" "URL: $URL" && curl -fsS "$URL/health" >/dev/null 2>&1 && log_success "Health OK" || warn "Health 未確認"
}

# ===== full-deploy（orchestrate） =====
cmd_full_deploy(){
  PROJECT_ID=${1:-}; [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID を指定してください"; shift || true
  local FLAGS=("$@")
  cmd_env "$PROJECT_ID"
  cmd_secrets "$PROJECT_ID" "${FLAGS[@]}"
  confirm "オプション機能（Calendar/Webhook/Timezone）も設定しますか?" && cmd_optional "$PROJECT_ID" || true
  cmd_deploy "$PROJECT_ID" "${REGION:-us-central1}"
  log_success "Full deploy 完了"
}

# ===== ar-clean（旧 cleanup-artifact-registry.sh） =====
cmd_ar_clean(){
  require_cmd gcloud jq
  local PROJECT_ID=${1:-}; local REGION=${2:-us-central1}; local REPO=${3:-mindbridge}; local IMAGE=${4:-mindbridge}; local KEEP=${5:-10}; local OLDER_DAYS=${6:-30}
  local DRY_RUN=true; [[ " $* " == *" --no-dry-run "* ]] && DRY_RUN=false
  [[ -z "$PROJECT_ID" ]] && die "Usage: mindbridge ar-clean <PROJECT_ID> [REGION] [REPO] [IMAGE] [KEEP] [OLDER_DAYS] [--no-dry-run]"
  local AR_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}"
  printf "%s\n" "[INFO] 対象: ${AR_PATH} KEEP=${KEEP} OLDER_THAN=${OLDER_DAYS}d DRY_RUN=${DRY_RUN}"
  local IMAGES_JSON; IMAGES_JSON=$(gcloud artifacts docker images list "$AR_PATH" --include-tags --format=json || echo '[]')
  local COUNT; COUNT=$(echo "$IMAGES_JSON" | jq 'length')
  (( COUNT == 0 )) && { printf "%s\n" "[INFO] 対象なし"; return 0; }
  local DELETABLE_DIGESTS; DELETABLE_DIGESTS=$(echo "$IMAGES_JSON" | jq -r --argjson keep "$KEEP" --argjson older "$OLDER_DAYS" '
    map({digest, created: (.createTime | fromdateiso8601)}) as $imgs
    | ($imgs | sort_by(.created) | reverse | .[:$keep] | map(.digest)) as $keep_digests
    | $imgs | map(select(.created < (now - ($older*86400))))
    | map(select(.digest as $d | ($keep_digests | index($d)) | not))
    | .[] | .digest')
  [[ -z "$DELETABLE_DIGESTS" ]] && { printf "%s\n" "[INFO] 条件により削除対象なし"; return 0; }
  printf "%s\n" "[PLAN] 削除予定:"; while read -r d; do [[ -n "$d" ]] && printf "  - %s\n" "${AR_PATH}@${d}"; done <<< "$DELETABLE_DIGESTS"
  [[ "$DRY_RUN" == true ]] && { printf "%s\n" "[DRY-RUN] --no-dry-run で実行"; return 0; }
  printf "%s\n" "[EXEC] 削除実行..."; local FAILED=0
  while read -r d; do [[ -z "$d" ]] && continue; gcloud artifacts docker images delete "${AR_PATH}@${d}" --quiet || FAILED=$((FAILED+1)); done <<< "$DELETABLE_DIGESTS"
  (( FAILED > 0 )) && { printf "%s\n" "[DONE] 完了（失敗: $FAILED）"; return 1; } || printf "%s\n" "[DONE] クリーンアップ完了"
}

# ===== init（旧 local-setup.sh） =====
cmd_init(){
  printf "%b\n" "${CYAN}MindBridge ローカル初期設定${NC}"
  if [[ -f .env ]]; then
    confirm ".env が存在します。上書きしますか?" || { echo "キャンセル"; return 0; }
  fi
  read -r -p "Discord Bot Token: " DISCORD_BOT_TOKEN
  read -r -p "Gemini API Key: " GEMINI_API_KEY
  local DEFAULT_VAULT="$HOME/Obsidian/MindBridge"
  read -r -p "Obsidian Vault パス [${DEFAULT_VAULT}]: " OBSIDIAN_VAULT_PATH; OBSIDIAN_VAULT_PATH=${OBSIDIAN_VAULT_PATH:-$DEFAULT_VAULT}
  read -r -p "Discord Guild ID (任意): " DISCORD_GUILD_ID
  cat > .env <<EOF
# Generated by scripts/manage.sh init
DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
GEMINI_API_KEY=${GEMINI_API_KEY}
OBSIDIAN_VAULT_PATH=${OBSIDIAN_VAULT_PATH}
DISCORD_GUILD_ID=${DISCORD_GUILD_ID}
ENVIRONMENT=personal
LOG_LEVEL=INFO
EOF
  mkdir -p "${OBSIDIAN_VAULT_PATH}"
  log_success ".env を作成しました"
}

cmd=${1:-help}
shift || true

case "$cmd" in
  help|-h|--help)
    usage
    ;;

  env)
    cmd_env "$@"
    ;;

  secrets)
    cmd_secrets "$@"
    ;;

  optional)
    cmd_optional "$@"
    ;;

  deploy)
    cmd_deploy "$@"
    ;;

  full-deploy)
    cmd_full_deploy "$@"
    ;;

  ar-clean)
    cmd_ar_clean "$@"
    ;;

  init)
    cmd_init "$@"
    ;;

  run)
    require_cmd uv
    [[ -f .env ]] || die ".env がありません。'cp .env.example .env' または './scripts/manage.sh init' を実行してください。"
    [[ -n "${MB_UV_MARK:-}" ]] && : > "${MB_UV_MARK}"
    [[ "${MB_DEBUG:-}" == 1 ]] && echo "[DEBUG] exec: uv run python -m src.main" 1>&2
    exec uv run python -m src.main
    ;;

  *)
    warn "未知のコマンド: $cmd"
    usage
    exit 2
    ;;
esac
