# MindBridge Cloud Run デプロイメントガイド

Google Cloud Run を使用して MindBridge を無料で運用するための完全ガイドです。**自動デプロイスクリプト**により 5 分でデプロイ完了、 GitHub 同期による Vault データの永続化を実現します。

## 🚀 クイックデプロイ（推奨）

**最短 5 分でデプロイ完了**：

```bash
# リポジトリをクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 完全自動デプロイ（音声認識・健康データ統合含む）
./scripts/full-deploy.sh YOUR_PROJECT_ID --with-optional

# 基本機能のみデプロイ
./scripts/full-deploy.sh YOUR_PROJECT_ID
```

**新機能**：
- ✨ Speech-to-Text 認証情報の自動生成
- ✨ Garmin Connect 簡単設定（ OAuth 不要）
- ✨ エラー処理とリトライ機能

## 事前準備

### 1. GitHub リポジトリの準備

```bash
# 1. プライベートリポジトリを作成
# GitHub で新しいプライベートリポジトリを作成: obsidian-vault

# 2. ローカルの Obsidian Vault を GitHub にプッシュ
cd /path/to/your/obsidian/vault
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/obsidian-vault.git
git push -u origin main
```

### 2. GitHub Personal Access Token の作成

1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" をクリック
3. スコープで `repo` にチェック
4. トークンを安全に保存

### 3. Google Cloud プロジェクトの設定

```bash
# Google Cloud CLI のインストール（未インストールの場合）
curl https://sdk.cloud.google.com | bash

# プロジェクトの設定
gcloud config set project YOUR_PROJECT_ID

# 請求先アカウントの確認（無料枠使用でも必要）
gcloud billing accounts list
gcloud billing projects link YOUR_PROJECT_ID --billing-account YOUR_BILLING_ACCOUNT_ID
```

## デプロイメント手順

### Step 1: API の有効化

```bash
# 必要な Google Cloud API を有効化
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage.googleapis.com
```

### Step 2: Secret Manager にシークレットを保存

```bash
# Discord Bot Token
echo -n "YOUR_DISCORD_BOT_TOKEN" | gcloud secrets create discord-bot-token --data-file=-

# Gemini API Key
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# GitHub Token （無料永続化用）
echo -n "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN" | gcloud secrets create github-token --data-file=-

# Obsidian Vault GitHub Repository URL
echo -n "https://github.com/username/obsidian-vault" | gcloud secrets create obsidian-backup-repo --data-file=-

# オプション: Google Cloud Speech API Key （音声認識用）
echo -n "YOUR_GOOGLE_CLOUD_SPEECH_API_KEY" | gcloud secrets create google-cloud-speech-api-key --data-file=-
```

### Step 3: 権限の設定

```bash
# Cloud Build に Secret Manager アクセス権限を付与
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding discord-bot-token \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding github-token \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding obsidian-backup-repo \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Step 4: アプリケーションのデプロイ

```bash
# MindBridge のソースコードディレクトリに移動
cd /path/to/mindbridge

# Cloud Build を使用してデプロイ
gcloud builds submit --config cloudbuild.yaml
```

### Step 5: 追加の環境変数設定（必要に応じて）

```bash
# Cloud Run サービスに追加の環境変数を設定
gcloud run services update mindbridge \
  --region us-central1 \
  --set-env-vars "OBSIDIAN_VAULT_PATH=/app/vault,OBSIDIAN_BACKUP_BRANCH=main,TZ=Asia/Tokyo"
```

## 動作確認

### デプロイメント状況の確認

```bash
# Cloud Run サービスの状態確認
gcloud run services describe mindbridge --region us-central1

# ログの確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mindbridge" --limit 50
```

### Discord ボットの確認

1. Discord サーバーでボットがオンラインになることを確認
2. `/health` コマンドでボットの状態確認
3. テストメッセージを送信して Obsidian Vault への保存を確認

### GitHub 同期の確認

```bash
# GitHub リポジトリを確認して新しいコミットがあることを確認
git log --oneline -5
```

## 費用最適化設定

Cloud Run の無料枠内で運用するための設定:

```bash
# インスタンスの最大数を制限（費用節約）
gcloud run services update mindbridge \
  --region us-central1 \
  --max-instances 3 \
  --min-instances 0

# メモリと CPU の制限（無料枠内）
gcloud run services update mindbridge \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. デプロイエラー
```bash
# ビルドログの詳細確認
gcloud builds list --limit 5
gcloud builds log BUILD_ID
```

#### 2. シークレットアクセスエラー
```bash
# 権限の再設定
gcloud secrets add-iam-policy-binding SECRET_NAME \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

#### 3. GitHub 同期エラー
- GitHub Token の権限を確認（`repo` スコープが必要）
- リポジトリの存在とアクセス権限を確認
- Cloud Run のログで詳細なエラーメッセージを確認

#### 4. ボットが応答しない
```bash
# Cloud Run サービスの再起動
gcloud run services update mindbridge --region us-central1
```

## 継続的デプロイメント

GitHub Actions を使用した自動デプロイ（オプション）:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - uses: google-github-actions/setup-gcloud@v1
      with:
        project_id: YOUR_PROJECT_ID
        service_account_key: ${{ secrets.GCP_SA_KEY }}

    - name: Deploy to Cloud Run
      run: gcloud builds submit --config cloudbuild.yaml
```

## モニタリングとメンテナンス

### 定期的な確認事項

1. **月次**: Google Cloud の無料枠使用量確認
2. **週次**: GitHub リポジトリのサイズ確認
3. **日次**: ボットの稼働状況確認

### ログ監視

```bash
# リアルタイムログ監視
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=mindbridge"

# エラーログのみ確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mindbridge AND severity>=ERROR" --limit 20
```

## セキュリティ考慮事項

1. **プライベートリポジトリ**: Obsidian Vault は必ずプライベートリポジトリで管理
2. **シークレット管理**: Google Secret Manager の適切な使用
3. **アクセス制御**: Cloud Run サービスへの適切なアクセス制限
4. **定期更新**: 依存関係とセキュリティパッチの定期更新

この設定により、 MindBridge を Google Cloud Run で無料運用し、 GitHub を使用した永続データ保存が実現されます。
