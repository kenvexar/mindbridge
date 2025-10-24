# shellcheck shell=bash

prompt_secret() {
  local secret_name=$1 desc=$2
  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
    warn "Secret '$secret_name' は既に存在します"
    [[ "$SKIP_EXISTING" == true ]] && { log "--skip-existing によりスキップ"; return 0; }
    confirm "更新しますか?" || { log "スキップ: $secret_name"; return 0; }
  else
    log "作成: $secret_name"
  fi
  echo "説明: $desc"
  read -rs -p "値を入力（入力は表示されません）: " secret_value
  echo
  [[ -z "$secret_value" ]] && { warn "空入力。スキップ"; return 1; }
  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
    printf %s "$secret_value" | gcloud secrets versions add "$secret_name" --project="$PROJECT_ID" --data-file=-
  else
    printf %s "$secret_value" | gcloud secrets create "$secret_name" --project="$PROJECT_ID" --data-file=-
  fi
  log_success "$secret_name 設定完了"
}

generate_speech_credentials() {
  local SA_NAME="mindbridge-speech"
  local SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
  local KEY_FILE="/tmp/mb-speech-$$.json"
  gcloud services enable speech.googleapis.com --quiet
  gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null || \
    gcloud iam service-accounts create "$SA_NAME" --display-name="MindBridge Speech Service Account"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA_EMAIL" --role="roles/speech.client" --quiet >/dev/null 2>&1 || true
  gcloud iam service-accounts keys create "$KEY_FILE" --iam-account="$SA_EMAIL"
  local json
  json=$(cat "$KEY_FILE")
  rm -f "$KEY_FILE"
  if gcloud secrets describe google-cloud-speech-credentials --project="$PROJECT_ID" &>/dev/null; then
    printf %s "$json" | gcloud secrets versions add google-cloud-speech-credentials --project="$PROJECT_ID" --data-file=-
  else
    printf %s "$json" | gcloud secrets create google-cloud-speech-credentials --project="$PROJECT_ID" --data-file=-
  fi
  log_success "google-cloud-speech-credentials を設定しました"
}

cmd_secrets() {
  PROJECT_ID=${1:-}
  shift || true
  [[ -z "$PROJECT_ID" ]] && die "PROJECT_ID を指定してください"
  ensure_gcloud_auth
  ensure_project_id
  SKIP_EXISTING=false
  WITH_OPTIONAL=false
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
  local s
  for s in discord-bot-token discord-guild-id gemini-api-key garmin-username garmin-password github-token obsidian-backup-repo google-cloud-speech-credentials; do
    gcloud secrets describe "$s" --project="$PROJECT_ID" &>/dev/null || continue
    gcloud secrets add-iam-policy-binding "$s" --member="serviceAccount:$SA_MAIN_EMAIL" --role="roles/secretmanager.secretAccessor" --project="$PROJECT_ID" 2>/dev/null || true
  done
  log_success "Secrets setup 完了"
}
