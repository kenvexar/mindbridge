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

generate_random_secret() {
  local secret_name=$1 desc=$2 length=${3:-48}
  local create_mode=create
  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
    warn "Secret '$secret_name' は既に存在します"
    if [[ "$SKIP_EXISTING" == true ]]; then
      log "--skip-existing によりスキップ"
      return 0
    fi
    confirm "再生成しますか?" || { log "スキップ: $secret_name"; return 0; }
    create_mode=update
  else
    log "自動生成: $secret_name ($desc)"
  fi

  local token
  token=$(python3 - <<PY
import secrets
import sys
print(secrets.token_urlsafe(${length}))
PY
)

  [[ -z "$token" ]] && die "$secret_name の生成に失敗しました"

  if [[ "$create_mode" == create ]]; then
    printf %s "$token" | gcloud secrets create "$secret_name" --project="$PROJECT_ID" --data-file=-
  else
    printf %s "$token" | gcloud secrets versions add "$secret_name" --project="$PROJECT_ID" --data-file=-
  fi
  log_success "$secret_name 自動設定完了"
}

cmd_secrets() {
  PROJECT_ID=${1:-}
  shift || true
  if [[ -z "$PROJECT_ID" ]]; then
    die "PROJECT_ID を指定してください"
  fi
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
  generate_random_secret health-endpoint-token "Health server shared token"
  generate_random_secret health-callback-state "OAuth callback CSRF token"
  generate_random_secret encryption-key "Application encryption key" 64

  if [[ "$WITH_OPTIONAL" == true ]]; then
    log_step "オプション（Google Calendar/Garmin/Speech）"
    prompt_secret google-calendar-client-id "Google Calendar OAuth Client ID"
    prompt_secret google-calendar-client-secret "Google Calendar OAuth Client Secret"
    prompt_secret garmin-username "Garmin Connect ユーザー名/メール"
    prompt_secret garmin-password "Garmin Connect パスワード"
    warn "Cloud Speech-to-Text は Workload Identity と ADC を利用してください（鍵生成ロジックは削除済み）"
  fi

  log_step "サービスアカウントへのアクセス許可付与"
  local SA_MAIN_EMAIL="mindbridge-service@${PROJECT_ID}.iam.gserviceaccount.com"
  local read_only_secrets=(
    discord-bot-token
    discord-guild-id
    gemini-api-key
    garmin-username
    garmin-password
    github-token
    obsidian-backup-repo
    health-endpoint-token
    health-callback-state
    encryption-key
    google-calendar-client-id
    google-calendar-client-secret
  )
  local write_secrets=(
    google-calendar-access-token
    google-calendar-refresh-token
  )
  local s
  for s in "${read_only_secrets[@]}" "${write_secrets[@]}"; do
    [[ -n "$s" ]] || continue
    gcloud secrets describe "$s" --project="$PROJECT_ID" &>/dev/null || continue
    gcloud secrets remove-iam-policy-binding "$s" \
      --member="serviceAccount:$SA_MAIN_EMAIL" \
      --role="roles/secretmanager.admin" \
      --project="$PROJECT_ID" \
      2>/dev/null || true
  done

  for s in "${read_only_secrets[@]}"; do
    gcloud secrets describe "$s" --project="$PROJECT_ID" &>/dev/null || continue
    gcloud secrets add-iam-policy-binding "$s" \
      --member="serviceAccount:$SA_MAIN_EMAIL" \
      --role="roles/secretmanager.secretAccessor" \
      --project="$PROJECT_ID" \
      2>/dev/null || true
  done

  for s in "${write_secrets[@]}"; do
    gcloud secrets describe "$s" --project="$PROJECT_ID" &>/dev/null || continue
    gcloud secrets add-iam-policy-binding "$s" \
      --member="serviceAccount:$SA_MAIN_EMAIL" \
      --role="roles/secretmanager.secretVersionAdder" \
      --project="$PROJECT_ID" \
      2>/dev/null || true
  done
  log_success "Secrets setup 完了"
}
