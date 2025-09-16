# MindBridge デプロイメントガイド

MindBridge の各種デプロイメント方法とその運用手順。

## 目次

1. [Google Cloud Run （推奨）](#google-cloud-run-推奨)
2. [ローカル Docker 運用](#ローカル-docker-運用)
3. [VPS 運用](#vps-運用)
4. [環境変数設定](#環境変数設定)
5. [バックアップとメンテナンス](#バックアップとメンテナンス)

## Google Cloud Run （推奨）

**月額約 8 円**で本格的な AI 知識管理システムを運用可能。

### 費用概算 (無料枠適用後)

| サービス | 無料枠 | 月額費用 |
|---------|-------|----------|
| Cloud Run | 200 万リクエスト/月 | **$0** |
| Artifact Registry | 0.5GB | **$0** |
| Cloud Build | 120 分/日 | **$0** |
| Secret Manager | 6 シークレット | **$0.06** |
| Gemini API | 1,500 回/日 | **$0** |
| Speech-to-Text | 60 分/月 | **$0** |
| **合計** | | **約$0.06/月 (8 円)** |

### クイックデプロイ（最短 5 分）

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
- Google Cloud 環境の自動セットアップ
- Speech-to-Text 認証情報の自動生成
- Garmin Connect 統合（ OAuth 不要）
- GitHub 同期によるデータ永続化
- エラー処理とリトライ機能

### 事前準備

**1. GitHub リポジトリの準備**

```bash
# 1) プライベートリポジトリを作成（例: obsidian-vault ）
# 2) ローカルの Obsidian Vault をプッシュ
cd /path/to/your/obsidian/vault
git init && git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/obsidian-vault.git
git push -u origin main
```

**2. Google Cloud CLI のセットアップ**

```bash
# Google Cloud CLI のインストール
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 認証
gcloud auth login
gcloud auth application-default login

# プロジェクト作成
export PROJECT_ID="mindbridge-$(date +%s)"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# 請求アカウントの関連付け (必須)
BILLING_ACCOUNT=$(gcloud billing accounts list --filter="open=true" --format="value(name)" --limit=1)
gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
```

### 詳細手順

推奨は自動デプロイスクリプトですが、手動実行の場合：

**Step 1: 環境設定**
```bash
./scripts/manage.sh env YOUR_PROJECT_ID
```

**Step 2: シークレット設定**
```bash
./scripts/manage.sh secrets YOUR_PROJECT_ID --with-optional
```

**Step 3: デプロイ実行**
```bash
./scripts/manage.sh deploy YOUR_PROJECT_ID
```

### 監視・費用管理

- **Cloud Console**: https://console.cloud.google.com/run
- **予算設定**: 50%/80%/100% のしきい値通知を設定
- **ログ確認**: `gcloud run services logs read mindbridge --region=us-central1`

### 基本原則

1. **無料枠活用**: 月額約 8 円での運用
2. **自動スケール**: アイドル時は費用ゼロ
3. **安全管理**: Secret Manager による認証情報保護
4. **永続化**: GitHub 同期による Vault データ保護

## ローカル Docker 運用

最も簡単な運用方法。 Docker がインストールされていれば即座に開始できます。

### 1. 環境設定

```bash
# 設定ファイルを準備
cp .env.docker.example .env.docker

# 設定を編集
vim .env.docker
```

必要な設定：
```env
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
GEMINI_API_KEY=your_api_key
OBSIDIAN_VAULT_PATH=/app/vault
```

### 2. 起動

```bash
# Docker Compose で起動
docker compose up -d
```

### 3. 確認

```bash
# ログ確認
docker compose logs -f

# ヘルスチェック
curl http://localhost:8080/health

# 停止
docker compose down
```

### 4. データ管理

- **Obsidian ボルト**: `./vault/` ディレクトリにマウント
- **ログ**: `./logs/` ディレクトリに保存
- **バックアップ**: `./backups/` ディレクトリに保存

## VPS 運用

24/7 運用したい場合は VPS での Docker 運用を推奨。

### 1. VPS 準備

```bash
# Docker インストール（ Ubuntu の例）
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose インストール
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. プロジェクト配置

```bash
# プロジェクトをクローン
git clone https://github.com/your-username/mindbridge.git
cd mindbridge

# 設定
cp .env.docker.example .env.docker
vim .env.docker
```

### 3. systemd サービス設定

`/etc/systemd/system/mindbridge.service`:
```ini
[Unit]
Description=MindBridge Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/mindbridge
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

起動設定：
```bash
sudo systemctl enable mindbridge
sudo systemctl start mindbridge
sudo systemctl status mindbridge
```

## 環境変数設定

### 必須設定

```env
# Discord 設定
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_discord_server_id

# AI 設定
GEMINI_API_KEY=your_gemini_api_key

# Obsidian 設定
OBSIDIAN_VAULT_PATH=/app/vault  # Docker 内パス
```

### オプション設定

```env
# 音声認識（オプション）
GOOGLE_APPLICATION_CREDENTIALS=/app/.config/gcp-credentials.json

# Garmin 統合（オプション）
GARMIN_EMAIL=your_email
GARMIN_PASSWORD=your_password

# GitHub バックアップ（オプション）
GITHUB_TOKEN=your_github_token
OBSIDIAN_BACKUP_REPO=your-username/obsidian-vault

# ログレベル
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## バックアップとメンテナンス

### 自動バックアップ

```bash
# cron ジョブでバックアップ
# 毎日 2:00 AM に実行
0 2 * * * cd /path/to/mindbridge && docker compose exec mindbridge-bot python -c "from src.obsidian.backup import backup_vault; backup_vault()"
```

### ログローテーション

```bash
# logrotate 設定例
/path/to/mindbridge/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 root root
}
```

### 更新手順

```bash
# 最新版に更新
git pull origin main

# コンテナ再ビルド・再起動
docker compose down
docker compose build
docker compose up -d

# ログ確認
docker compose logs -f
```

### トラブルシューティング

```bash
# コンテナ状態確認
docker compose ps

# リソース使用量確認
docker stats

# ログ確認
docker compose logs --tail=100 mindbridge-bot

# コンテナ内シェル
docker compose exec mindbridge-bot /bin/bash

# 強制再起動
docker compose down --remove-orphans
docker compose up -d --force-recreate
```

## 監視

### ヘルスチェック

```bash
# 定期ヘルスチェック
*/5 * * * * curl -f http://localhost:8080/health || echo "MindBridge is down" | mail -s "Alert" your@email.com
```

### 簡易監視スクリプト

`monitor.sh`:
```bash
#!/bin/bash
SERVICE="mindbridge"

if ! docker compose ps | grep -q "$SERVICE.*Up"; then
    echo "Service $SERVICE is down. Restarting..."
    docker compose up -d
    echo "Service restarted at $(date)" >> restart.log
fi
```

実行：
```bash
# 5 分おきに監視
*/5 * * * * /path/to/mindbridge/monitor.sh
```
