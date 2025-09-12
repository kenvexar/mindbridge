# MindBridge デプロイスクリプト

MindBridge を Google Cloud Run に自動デプロイするためのスクリプト集です。

## 🚀 クイックスタート

### 1. 完全自動デプロイ（推奨）

```bash
# 基本機能のみ
./scripts/full-deploy.sh your-project-id

# オプション機能も含める
./scripts/full-deploy.sh your-project-id --with-optional
```

このコマンド一つで環境セットアップからデプロイまで全て自動実行されます。

## 📋 個別スクリプト

### 環境セットアップ

```bash
./scripts/setup-environment.sh <PROJECT_ID>
```

- Google Cloud プロジェクト設定
- 必要な API の有効化
- サービスアカウント作成
- Cloud Run 環境準備

### シークレット設定

```bash
./scripts/setup-secrets.sh <PROJECT_ID>
```

必須シークレット:
- `discord-bot-token` - Discord Bot Token
- `discord-guild-id` - Discord サーバー ID
- `gemini-api-key` - Google Gemini API Key
- `github-token` - GitHub Personal Access Token
- `obsidian-backup-repo` - GitHub リポジトリ URL

オプションシークレット:
- `garmin-username` - Garmin Connect ユーザー名/メール
- `garmin-password` - Garmin Connect パスワード
- `google-cloud-speech-credentials` - Speech-to-Text JSON 認証情報（自動生成可能）

### オプション機能設定

```bash
./scripts/setup-optional-features.sh <PROJECT_ID>
```

オプション機能:
- 🎤 **音声メモ機能** - Google Cloud Speech-to-Text （自動認証情報生成）
- 💪 **健康データ統合** - Garmin Connect （ python-garminconnect 、 OAuth 不要）
- 📅 **カレンダー統合** - Google Calendar API
- 🔔 **Webhook 通知** - Slack/Discord Webhook
- ⚙️ **管理者設定** - 管理者ユーザー、タイムゾーン

**新機能ハイライト**:
- ✨ Speech-to-Text 認証情報の自動生成機能
- ✨ Garmin Connect 簡単設定（ OAuth 不要、ユーザー名/パスワード方式）
- ✨ エラー処理とリトライ機能による高い安定性

### デプロイ実行

```bash
./scripts/deploy.sh <PROJECT_ID>
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

## 📁 スクリプト一覧

| スクリプト | 用途 | 必須 | 新機能 |
|-----------|------|------|-------|
| `full-deploy.sh` | **完全自動デプロイ** | ⭐ **推奨** | ✨ 統合済み |
| `setup-environment.sh` | Google Cloud 環境セットアップ | ✅ 必須 | ✨ サービスアカウント修正 |
| `setup-secrets.sh` | 必須シークレット設定 | ✅ 必須 | ✨ Garmin 対応 |
| `setup-optional-features.sh` | オプション機能設定 | 🔧 任意 | ✨ 改良済み |
| `deploy.sh` | Cloud Run デプロイ実行 | ✅ 必須 | - |
| `generate-speech-credentials.sh` | **Speech 認証情報生成** | 🎤 音声機能用 | ✨ **新規** |
| `docker-local-test.sh` | ローカル Docker テスト | 🧪 開発用 | - |

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
