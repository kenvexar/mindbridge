# MindBridge 安全デプロイ手順書

## **今後の完全手順ガイド**

---

## **STEP 1: 緊急認証情報対応（即座実行）**

### **1.1 Discord Bot Token 更新**
```bash
# 1. Discord Developer Portal にアクセス
# https://discord.com/developers/applications

# 2. アプリケーション選択 → Bot → Reset Token
# 3. 新しいトークンをコピーして安全に保存
```

### **1.2 Google API Key 更新**
```bash
# 1. Google Cloud Console にアクセス
# https://console.cloud.google.com/apis/credentials

# 2. 該当 API Key を削除
# 3. 新しい API Key を作成
# - Gemini API 用
# - Google Cloud Speech API 用
```

### **1.3 GitHub Token 更新**
```bash
# 1. GitHub Settings にアクセス
# https://github.com/settings/tokens

# 2. 該当トークンを Revoke
# 3. 新しい Personal Access Token を作成
# - repo (Full control of private repositories)
# - workflow (Update GitHub Action workflows)
```

### **1.4 Garmin 認証情報更新**
```bash
# 1. Garmin Connect アカウント設定
# https://connect.garmin.com/

# 2. パスワード変更
# 3. 新しい認証情報を記録
```

---

## **STEP 2: ローカル環境設定（ 15 分）**

### **2.1 環境変数ファイル作成**
```bash
# サンプルを複製して Docker 用設定ファイルを作成
cp .env.docker.example .env.docker

# 以下の値を最新の認証情報に更新
DISCORD_BOT_TOKEN=<Discord の新しい Bot Token>
GEMINI_API_KEY=<Google Gemini API Key>
GOOGLE_CLOUD_SPEECH_API_KEY=<Speech-to-Text API Key>
GITHUB_TOKEN=<GitHub Personal Access Token>
GARMIN_EMAIL=<Garmin ログインメール>
GARMIN_PASSWORD=<Garmin パスワード>
OBSIDIAN_BACKUP_REPO=<Vault を保存する GitHub リポジトリ URL>
```

### **2.2 ローカル動作確認**
```bash
# 依存関係が最新であることを確認
uv sync --dev

# 全テストを実行
uv run pytest -q

# コード品質チェック
uv run ruff check . --fix
uv run mypy src

# ローカル起動テスト
uv run python -m src.main
```

---

## **STEP 3: Google Cloud 環境準備（ 30 分）**

### **3.1 プロジェクト設定**
```bash
# Google Cloud にログイン
gcloud auth login

# プロジェクト ID を設定（例: mindbridge-prod-2024 ）
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 必要な API を有効化
./scripts/manage.sh env $PROJECT_ID
```

### **3.2 Secret Manager 設定**
```bash
# 必須シークレット設定
./scripts/manage.sh secrets $PROJECT_ID

# 実行時にプロンプトされる項目:
# - Discord Bot Token
# - Gemini API Key
# - GitHub Token
# - Obsidian Backup Repo URL
# - Garmin 認証情報

# オプション機能も設定する場合
./scripts/manage.sh secrets $PROJECT_ID --with-optional
```

### **3.3 サービスアカウント確認**
```bash
# サービスアカウントが正しく設定されているか確認
gcloud iam service-accounts list --filter="email:mindbridge-service@$PROJECT_ID.iam.gserviceaccount.com"

# 権限確認
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:mindbridge-service@$PROJECT_ID.iam.gserviceaccount.com"
```

---

## **STEP 4: デプロイ前テスト（ 20 分）**

### **4.1 ローカル本番モード確認**
```bash
# 本番モードでローカル起動
ENVIRONMENT=production uv run python -m src.main

# Discord Slash コマンド動作確認:
# - /status → Bot 稼働確認
# - /system_status → スケジューラと外部連携の状態
# - /garmin_today → Garmin データ取得確認（オプション）
# - 音声メモアップロード → 文字起こし動作確認
```

### **4.2 Google Secret Manager 接続テスト**
```bash
# Secret Manager からシークレット取得テスト
gcloud secrets versions access latest --secret="discord-bot-token" --project=$PROJECT_ID

# 他の必須シークレットも確認
gcloud secrets versions access latest --secret="gemini-api-key" --project=$PROJECT_ID
gcloud secrets versions access latest --secret="github-token" --project=$PROJECT_ID
```

---

## **STEP 5: Cloud Run デプロイ（ 15 分）**

### **5.1 一括デプロイ実行**
```bash
# 基本機能のみでデプロイ
./scripts/manage.sh full-deploy $PROJECT_ID

# または、オプション機能も含めてデプロイ
./scripts/manage.sh full-deploy $PROJECT_ID --with-optional
```

### **5.2 デプロイ状況確認**
```bash
# サービス状態確認
gcloud run services describe mindbridge --region=us-central1 --project=$PROJECT_ID

# ログ確認
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=mindbridge" \
  --project=$PROJECT_ID --limit=50
```

### **5.3 ヘルスチェック確認**
```bash
# Cloud Run URL 取得
SERVICE_URL=$(gcloud run services describe mindbridge --region=us-central1 --project=$PROJECT_ID --format="value(status.url)")

# ヘルスエンドポイント確認
curl -f "$SERVICE_URL/health"

# 期待される応答: {"status": "healthy", "timestamp": "..."}
```

---

## **STEP 6: 本番動作確認（ 10 分）**

### **6.1 Discord Bot 動作確認**
```bash
# Discord サーバーで以下をテスト:
/status             # → Bot の状態確認
/integration_status # → 外部連携サマリー
/garmin_sleep       # → Garmin 睡眠データ確認（設定済みの場合）
```

### **6.2 主要機能テスト**
1. **メッセージ処理**: #memo チャンネルにテストメッセージ投稿
2. **音声処理**: 音声ファイルをアップロード → 文字起こし確認
3. **GitHub 同期**: Obsidian Vault のバックアップ動作確認

### **6.3 監視設定確認**
```bash
# Cloud Run メトリクス確認
gcloud logging read "resource.type=cloud_run_revision" \
  --project=$PROJECT_ID --limit=20

# エラーログがないことを確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --project=$PROJECT_ID --limit=10
```

---

## **STEP 7: 運用開始後の監視（継続）**

### **7.1 日次チェック項目**
```bash
# サービス状態確認
gcloud run services list --project=$PROJECT_ID

# エラーログ確認（毎日）
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --project=$PROJECT_ID --freshness=1d

# コスト確認
gcloud billing budgets list --billing-account=YOUR_BILLING_ACCOUNT
```

### **7.2 週次メンテナンス**
```bash
# 古いコンテナイメージ削除
./scripts/manage.sh ar-clean $PROJECT_ID us-central1 mindbridge mindbridge 5 7

# セキュリティアップデート確認
uv sync --upgrade
```

---

## **トラブルシューティング**

### **よくある問題と解決方法**

#### **問題 1: デプロイ時の認証エラー**
```bash
# 解決方法
gcloud auth login
gcloud config set project $PROJECT_ID
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### **問題 2: Discord Bot が応答しない**
```bash
# 解決方法
# 1. Secret Manager のトークン確認
gcloud secrets versions access latest --secret="discord-bot-token" --project=$PROJECT_ID

# 2. Discord Developer Portal でトークン再確認
# 3. Bot 権限設定確認（管理者権限推奨）
```

#### **問題 3: Cloud Run 起動失敗**
```bash
# 解決方法
# 1. ログ詳細確認
gcloud logs read "resource.type=cloud_run_revision" --project=$PROJECT_ID --limit=100

# 2. 環境変数確認
gcloud run services describe mindbridge --region=us-central1 --project=$PROJECT_ID

# 3. リソース制限確認（メモリ・ CPU ）
```

---

## **成功確認チェックリスト**

- [ ] 全ての認証情報を新規作成・設定完了
- [ ] ローカル環境で正常動作確認
- [ ] Google Cloud 環境設定完了
- [ ] Secret Manager にシークレット保存完了
- [ ] Cloud Run デプロイ成功
- [ ] ヘルスチェック正常応答
- [ ] Discord Bot 応答確認
- [ ] 主要機能動作確認
- [ ] エラーログなし
- [ ] 監視体制構築完了

**全項目完了後、安全にサービス運用開始可能です！**

---

## **緊急時の対応**

### **サービス停止が必要な場合**
```bash
# 緊急停止
gcloud run services update mindbridge --region=us-central1 --project=$PROJECT_ID --min-instances=0 --max-instances=0

# 復旧
gcloud run services update mindbridge --region=us-central1 --project=$PROJECT_ID --min-instances=0 --max-instances=3
```

### **認証情報漏洩時の対応**
1. 該当トークン・ API キーの即座無効化
2. 新しい認証情報の生成
3. Secret Manager での更新
4. サービス再デプロイ

**これで完全に安全なデプロイが可能です！**

---

## **関連ドキュメント**

- [プロジェクト README](../README.md)
- [開発ガイド](../CLAUDE.md)
- [セキュリティドキュメント](SECURITY.md)
- [運用ガイド](OPERATIONS.md)

---

**作成日**: 2025 年 9 月 23 日
**更新日**: 2025 年 9 月 23 日
**バージョン**: 1.0
