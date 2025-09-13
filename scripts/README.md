# MindBridge デプロイ/運用 CLI

MindBridge を Google Cloud Run に自動デプロイ/運用するための統合 CLI です。

## 🚀 クイックスタート

### 1. 完全自動デプロイ（推奨）

```bash
# 基本機能のみ
./scripts/manage.sh full-deploy your-project-id

# オプション機能も含める
./scripts/manage.sh full-deploy your-project-id --with-optional
```

このコマンド一つで環境セットアップからデプロイまで全て自動実行されます。

## 📋 統合 CLI（mindbridge）

単一エントリは `scripts/manage.sh` です（以下コマンドはすべてこれ経由）。

主なサブコマンド:
- `env <PROJECT_ID>`: Google Cloud 環境セットアップ
- `secrets <PROJECT_ID> [--with-optional] [--skip-existing]`: シークレット設定（Garmin/Speech 自動生成対応）
- `optional <PROJECT_ID>`: Calendar/Webhook/Timezone 設定
- `deploy <PROJECT_ID> [REGION]`: Cloud Run デプロイ
- `full-deploy <PROJECT_ID> [FLAGS]`: 一括実行（env → secrets → optional → deploy）
- `ar-clean <PROJECT_ID> [...]`: Artifact Registry クリーンアップ
- `init`: `.env` 初期生成（ローカル）
- `run`: ローカル起動（`.env` 必須）

**主な機能**:
- ✨ Speech-to-Text 認証情報の自動生成機能
- ✨ Garmin Connect 簡単設定（ OAuth 不要、ユーザー名/パスワード方式）
- ✨ エラー処理とリトライ機能による高い安定性

### デプロイ実行（個別）

```bash
./scripts/manage.sh deploy <PROJECT_ID> [REGION]
```

- Cloud Build によるデプロイ
- ヘルスチェック
- サービス確認

## 🔧 事前準備

### 1. Google Cloud SDK

```bash
# gcloud CLI インストール
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 認証
gcloud auth login
```

### 2. Discord Bot 作成

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリ作成
2. Bot タブで Bot 作成
3. `MESSAGE CONTENT INTENT` と `SERVER MEMBERS INTENT` を ON
4. Token をコピー

### 3. Gemini API Key

1. [Google AI Studio](https://makersuite.google.com/app/apikey) で API Key 作成
2. API Key をコピー

### 4. GitHub リポジトリ

1. プライベートリポジトリ作成（ Obsidian vault backup 用）
2. Personal Access Token 作成（`repo` スコープ）

## 📁 コマンド一覧（`manage.sh`）

- `env <PROJECT_ID>`: Google Cloud 環境セットアップ
- `secrets <PROJECT_ID> [--with-optional] [--skip-existing]`: シークレット設定
- `optional <PROJECT_ID>`: Calendar/Webhook/Timezone 設定
- `deploy <PROJECT_ID> [REGION]`: Cloud Run デプロイ
- `full-deploy <PROJECT_ID> [FLAGS]`: 一括実行（env → secrets → optional → deploy）
- `ar-clean <PROJECT_ID> [...]`: Artifact Registry クリーンアップ
- `init`: `.env` 初期生成（ローカル）
- `run`: ローカル起動（`.env` 必須）

## 🎯 デプロイ後の確認

### 1. サービス確認

```bash
# サービス状況
gcloud run services describe mindbridge --region=us-central1

# ログ確認
gcloud logs tail --service=mindbridge

# URL 確認
gcloud run services list
```

### 2. Discord テスト

1. Bot を個人サーバーに招待
2. 必要なチャンネル作成:
   - `#memo` - メイン入力チャンネル
   - `#notifications` - システム通知
   - `#commands` - ボットコマンド
3. `#memo` でテストメッセージ送信

### 3. 機能テスト

```bash
# 音声メモテスト
# Discord に音声ファイルを送信

# 健康データテスト
# Discord で /garmin_sync コマンド

# スケジュールテスト
# Discord で /schedule コマンド
```

## 🔒 セキュリティ

- すべての認証情報は Google Secret Manager で暗号化保存
- サービスアカウントは最小権限の原則
- プライベート GitHub リポジトリ使用推奨

## 💰 費用

基本的に無料枠内で運用可能:
- Cloud Run: 月 200 万リクエストまで無料
- Secret Manager: 6 シークレットまで無料
- Cloud Build: 月 120 分まで無料

## 🐛 トラブルシューティング

### よくあるエラー

```bash
# API が有効化されていない
gcloud services enable run.googleapis.com

# 権限エラー
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# シークレット作成エラー
gcloud services enable secretmanager.googleapis.com
```

### デバッグコマンド

```bash
# デプロイ詳細ログ
gcloud builds log --stream

# サービス詳細
gcloud run services describe mindbridge --region=us-central1

# シークレット確認
gcloud secrets list
```

## 📞 サポート

問題が発生した場合:
1. ログを確認: `gcloud logs tail --service=mindbridge`
2. [Issues](https://github.com/kenvexar/mindbridge/issues) に報告
3. デバッグ情報を添付してください

---

**Happy Deploying! 🚀**
