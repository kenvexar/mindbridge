# MindBridge Cloud Run デプロイメントガイド

Google Cloud Run を使用して MindBridge を無料枠中心で運用するための詳細ガイドです。自動デプロイスクリプトにより最短 5 分でデプロイ可能、GitHub 同期による Obsidian Vault データの永続化にも対応します。イメージは Artifact Registry に保存します。

## クイックデプロイ（推奨）

```bash
# リポジトリをクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 完全自動デプロイ（音声認識・健康データ統合含む）
./scripts/manage.sh full-deploy YOUR_PROJECT_ID --with-optional

# 基本機能のみデプロイ
./scripts/manage.sh full-deploy YOUR_PROJECT_ID
```

主な特徴：
- Speech-to-Text 認証情報の自動生成
- Garmin Connect 簡単設定（OAuth 不要）
- GitHub 同期で Vault 永続化
- エラー処理とリトライ

## 事前準備

### 1. GitHub リポジトリの準備

```bash
# 1) プライベートリポジトリを作成（例: obsidian-vault）
# 2) ローカルの Obsidian Vault をプッシュ
cd /path/to/your/obsidian/vault
git init && git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/obsidian-vault.git
git push -u origin main
```

### 2. GitHub Personal Access Token の作成
Developer settings → Tokens (classic) → repo スコープを付与して作成し、安全に保管します。

### 3. Google Cloud プロジェクト設定

```bash
curl https://sdk.cloud.google.com | bash
gcloud config set project YOUR_PROJECT_ID

# 請求アカウントの関連付け（無料枠でも必要）
gcloud billing projects link YOUR_PROJECT_ID --billing-account YOUR_BILLING_ACCOUNT_ID
```

## デプロイ手順

### Step 1: API 有効化
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com storage.googleapis.com artifactregistry.googleapis.com
```

### Step 2: Secret Manager 設定
```bash
echo -n "YOUR_DISCORD_BOT_TOKEN" | gcloud secrets create discord-bot-token --data-file=-
echo -n "YOUR_GEMINI_API_KEY"   | gcloud secrets create gemini-api-key      --data-file=-
echo -n "YOUR_GITHUB_PAT"       | gcloud secrets create github-token        --data-file=-
echo -n "https://github.com/username/obsidian-vault" | \
  gcloud secrets create obsidian-backup-repo --data-file=-

# オプション: Speech-to-Text
echo -n "YOUR_GOOGLE_CLOUD_SPEECH_API_KEY" | \
  gcloud secrets create google-cloud-speech-api-key --data-file=-
```

### Step 3: 権限設定（Cloud Build → Secret Manager）
```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
for s in discord-bot-token gemini-api-key github-token obsidian-backup-repo; do
  gcloud secrets add-iam-policy-binding "$s" \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

### Step 4: Artifact Registry リポジトリの作成
```bash
gcloud artifacts repositories create mindbridge \
  --repository-format=docker \
  --location=us-central1
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Step 5: デプロイ
```bash
cd /path/to/mindbridge
gcloud builds submit --config deploy/cloudbuild.yaml
```

## ローカル/Docker 検証
```bash
cp .env.docker.example .env.docker
docker compose up -d
```

ヘルスチェック：
```bash
curl http://localhost:8080/health
```

## 代表的な環境変数
```env
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
GEMINI_API_KEY=...
OBSIDIAN_VAULT_PATH=/app/vault
# オプション
GOOGLE_APPLICATION_CREDENTIALS=/app/.config/gcp-credentials.json
GARMIN_EMAIL=...
GARMIN_PASSWORD=...
GITHUB_TOKEN=...
OBSIDIAN_BACKUP_REPO=your-username/obsidian-vault
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## 運用のヒント
- Cloud Run: `min-instances=0` でアイドル時コストゼロ
- 予算アラートを設定して使い過ぎ防止
- 定期バックアップとログ確認を習慣化

補足: `cloud-run.yaml` は `autoscaling.knative.dev/minScale: "0"`、`containerConcurrency: 10` に統一しています。Cloud Build のデプロイフラグとも整合します。

## Artifact Registry のイメージ参照例
`us-central1-docker.pkg.dev/YOUR_PROJECT_ID/mindbridge/mindbridge:latest`
