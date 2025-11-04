# shellcheck shell=bash

cmd_optional() {
  PROJECT_ID=${1:-}
  if [[ -z "$PROJECT_ID" ]]; then
    die "PROJECT_ID を指定してください"
  fi
  ensure_gcloud_auth
  ensure_project_id

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
  read -r -p "タイムゾーン [Asia/Tokyo]: " TIMEZONE || true
  TIMEZONE=${TIMEZONE:-Asia/Tokyo}
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
