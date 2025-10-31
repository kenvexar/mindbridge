# shellcheck shell=bash

cmd_env() {
  PROJECT_ID=${1:-}
  if [[ -z "$PROJECT_ID" ]]; then
    die "PROJECT_ID を指定してください"
  fi
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
