# shellcheck shell=bash

cmd_deploy_precheck() {
  local PROJECT_ID=${1:-}
  shift || true
  if [[ -z "$PROJECT_ID" ]]; then
    die "PROJECT_ID を指定してください"
  fi

  local REGION="us-central1" SKIP_TESTS=false SKIP_MYPY=false SKIP_SECRET_CHECK=false SKIP_SA_CHECK=false SKIP_ARTIFACT_CHECK=false
  while (($#)); do
    case "$1" in
      --region)
        shift
        REGION=${1:-$REGION}
        ;;
      --region=*)
        REGION=${1#*=}
        ;;
      --skip-tests)
        SKIP_TESTS=true
        ;;
      --skip-mypy)
        SKIP_MYPY=true
        ;;
      --skip-secret-checks)
        SKIP_SECRET_CHECK=true
        ;;
      --skip-sa-checks)
        SKIP_SA_CHECK=true
        ;;
      --skip-artifact-check)
        SKIP_ARTIFACT_CHECK=true
        ;;
      --help|-h)
        cat <<'HELP'
Usage: ./scripts/manage.sh deploy-precheck <PROJECT_ID> [--region REGION]
       [--skip-tests] [--skip-mypy] [--skip-secret-checks]
       [--skip-sa-checks] [--skip-artifact-check]
HELP
        return 0
        ;;
      *)
        warn "未対応のオプション: $1"
        ;;
    esac
    shift || true
  done

  ensure_repo_root
  require_cmd git gcloud
  ensure_gcloud_auth
  gcloud config set project "$PROJECT_ID" --quiet

  log_step "Git 作業ツリー確認"
  local DIRTY
  DIRTY=$(git status --porcelain)
  if [[ -n "$DIRTY" ]]; then
    warn "未コミットの変更があります"
    confirm "このまま続行しますか?" || die "作業ツリーをクリーンにして再実行してください"
  else
    log "作業ツリーはクリーンです"
  fi

  if [[ "$SKIP_TESTS" == false ]]; then
    require_cmd uv
    log_step "pytest 実行"
    uv run pytest -q || die "uv run pytest -q が失敗しました"
    log_step "ruff check 実行"
    uv run ruff check . || die "uv run ruff check . が失敗しました"
    if [[ "$SKIP_MYPY" == false ]]; then
      log_step "mypy 実行"
      if ! uv run mypy src; then
        warn "mypy でエラーが検出されました"
        confirm "mypy エラーを無視して続行しますか?" || die "mypy を修正してから再試行してください"
      fi
    else
      warn "--skip-mypy により mypy をスキップしました"
    fi
  else
    warn "--skip-tests により pytest/ruff をスキップしました"
  fi

  log_step "gcloud 認証状態"
  local ACTIVE_ACCOUNT
  ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)
  if [[ -z "$ACTIVE_ACCOUNT" ]]; then
    die "gcloud にアクティブなアカウントがありません"
  fi
  log "Active account: $ACTIVE_ACCOUNT"

  if [[ "$SKIP_SECRET_CHECK" == false ]]; then
    log_step "Secret Manager 必須項目"
    local secrets=(discord-bot-token discord-guild-id gemini-api-key github-token obsidian-backup-repo google-cloud-speech-credentials health-endpoint-token health-callback-state)
    local missing=()
    local secret
    for secret in "${secrets[@]}"; do
      local exists
      exists=$(gcloud secrets describe "$secret" --project="$PROJECT_ID" --format='value(name)' 2>/dev/null || true)
      if [[ -z "$exists" ]]; then
        missing+=("$secret")
        continue
      fi
      local version_state
      version_state=$(gcloud secrets versions list "$secret" --project="$PROJECT_ID" --filter="state=ENABLED" --limit=1 --format='value(state)' 2>/dev/null || true)
      if [[ -z "$version_state" ]]; then
        missing+=("$secret")
      fi
    done
    if (( ${#missing[@]} )); then
      log_error "Secret Manager に不足があります: ${missing[*]}"
      die "シークレットを設定してから再試行してください"
    fi
  else
    warn "--skip-secret-checks によりシークレット確認をスキップしました"
  fi

  if [[ "$SKIP_SA_CHECK" == false ]]; then
    log_step "サービスアカウント権限"
    local SA_EMAIL="mindbridge-service@${PROJECT_ID}.iam.gserviceaccount.com"
    local roles=(roles/secretmanager.secretAccessor roles/logging.logWriter roles/monitoring.metricWriter roles/cloudtrace.agent roles/speech.client)
    local missing_roles=()
    local role
    for role in "${roles[@]}"; do
      local has_role
      has_role=$(gcloud projects get-iam-policy "$PROJECT_ID" --flatten="bindings[].members" --filter="bindings.role=$role AND bindings.members=serviceAccount:$SA_EMAIL" --format='value(bindings.members)' 2>/dev/null || true)
      [[ "$has_role" == "serviceAccount:$SA_EMAIL" ]] || missing_roles+=("$role")
    done
    if (( ${#missing_roles[@]} )); then
      log_error "サービスアカウントに不足しているロール: ${missing_roles[*]}"
      die "IAM 設定を更新してから再試行してください"
    fi
  else
    warn "--skip-sa-checks によりサービスアカウント確認をスキップしました"
  fi

  if [[ "$SKIP_ARTIFACT_CHECK" == false ]]; then
    log_step "Artifact Registry 状態"
    if ! gcloud artifacts repositories describe mindbridge --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
      die "Artifact Registry 'mindbridge' が ${REGION} に存在しません"
    fi
    gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/mindbridge/mindbridge" --limit=1 >/dev/null 2>&1 || warn "コンテナイメージがまだ登録されていません"
  else
    warn "--skip-artifact-check により Artifact Registry 確認をスキップしました"
  fi

  log_success "precheck 完了"
}

cmd_deploy() {
  PROJECT_ID=${1:-}
  REGION=${2:-us-central1}
  if [[ -z "$PROJECT_ID" ]]; then
    die "PROJECT_ID を指定してください"
  fi
  ensure_gcloud_auth
  ensure_project_id
  local SERVICE_NAME=mindbridge
  local IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/mindbridge/mindbridge"
  log_step "必要 API を有効化"
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com --project="$PROJECT_ID" --quiet
  log_step "Artifact Registry リポジトリ確認"
  gcloud artifacts repositories describe mindbridge --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1 || \
    gcloud artifacts repositories create mindbridge --repository-format=docker --location="$REGION" --project="$PROJECT_ID"

  log_step "Cloud Build によるビルド/デプロイ"
  local CB_CONFIG="deploy/cloudbuild.yaml"
  [[ -f "$CB_CONFIG" ]] || die "deploy/cloudbuild.yaml が見つかりません"
  local IMAGE_TAG
  IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)
  local BUILD_ID
  BUILD_ID=$(gcloud builds submit \
    --config "$CB_CONFIG" \
    --project="$PROJECT_ID" \
    --substitutions="_IMAGE_TAG=${IMAGE_TAG}" \
    --format='value(id)') || die "Cloud Build 失敗"
  log_success "Cloud Build 完了 (Build ID: $BUILD_ID)"

  log_step "Cloud Run へ反映"
  local CR_CONFIG="deploy/cloud-run.yaml"
  [[ -f "$CR_CONFIG" ]] || die "deploy/cloud-run.yaml が見つかりません"
  if grep -q "PROJECT_ID" "$CR_CONFIG"; then
    sed "s/PROJECT_ID/$PROJECT_ID/g" "$CR_CONFIG" > /tmp/cloud-run-deploy.yaml
  else
    cp "$CR_CONFIG" /tmp/cloud-run-deploy.yaml
  fi
  gcloud run services replace /tmp/cloud-run-deploy.yaml --region="$REGION" --project="$PROJECT_ID"
  local SECRET_BINDINGS="DISCORD_BOT_TOKEN=discord-bot-token:latest,DISCORD_GUILD_ID=discord-guild-id:latest,GEMINI_API_KEY=gemini-api-key:latest,GITHUB_TOKEN=github-token:latest,OBSIDIAN_BACKUP_REPO=obsidian-backup-repo:latest,GOOGLE_CLOUD_SPEECH_CREDENTIALS=google-cloud-speech-credentials:latest,HEALTH_ENDPOINT_TOKEN=health-endpoint-token:latest,HEALTH_CALLBACK_STATE=health-callback-state:latest,ENCRYPTION_KEY=encryption-key:latest"
  gcloud run services update "$SERVICE_NAME" \
    --image="${IMAGE_NAME}:${IMAGE_TAG}" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --set-secrets="${SECRET_BINDINGS}" \
    --set-env-vars="SECRET_MANAGER_PROJECT_ID=${PROJECT_ID},SECRET_MANAGER_STRATEGY=google" || true
  rm -f /tmp/cloud-run-deploy.yaml

  log_step "Health Check"
  local URL
  URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')
  if [[ -n "$URL" ]]; then
    printf "%s\n" "URL: $URL"
    if curl -fsS "$URL/health" >/dev/null 2>&1; then
      log_success "Health OK"
    else
      warn "Health 未確認"
    fi
  else
    warn "Cloud Run URL を取得できませんでした"
  fi
}

cmd_deploy_auto() {
  local PROJECT_ID=${1:-}
  shift || true
  if [[ -z "$PROJECT_ID" ]]; then
    die "PROJECT_ID を指定してください"
  fi
  local REGION="us-central1"
  if (($#)) && [[ $1 != --* ]]; then
    REGION=$1
    shift || true
  fi
  local PRECHECK_FLAGS=("--region=$REGION")
  while (($#)); do
    PRECHECK_FLAGS+=("$1")
    shift || true
  done
  cmd_deploy_precheck "$PROJECT_ID" "${PRECHECK_FLAGS[@]}"
  cmd_deploy "$PROJECT_ID" "$REGION"
}

cmd_full_deploy() {
  PROJECT_ID=${1:-}
  if [[ -z "$PROJECT_ID" ]]; then
    die "PROJECT_ID を指定してください"
  fi
  shift || true
  local FLAGS=("$@")
  cmd_env "$PROJECT_ID"
  cmd_secrets "$PROJECT_ID" "${FLAGS[@]}"
  confirm "オプション機能（Calendar/Webhook/Timezone）も設定しますか?" && cmd_optional "$PROJECT_ID" || true
  cmd_deploy "$PROJECT_ID" "${REGION:-us-central1}"
  log_success "Full deploy 完了"
}
