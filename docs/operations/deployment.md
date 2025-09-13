# 簡単デプロイメントガイド

MindBridge をシンプルに運用する手順。

## 目次

1. [推奨デプロイメント方法](#推奨デプロイメント方法)
2. [ローカル Docker 運用](#ローカル-docker-運用)
3. [VPS 運用](#vps-運用)
4. [環境変数設定](#環境変数設定)
5. [バックアップとメンテナンス](#バックアップとメンテナンス)

## 🎯 推奨デプロイメント方法

以下の順序で検討することを推奨：

```
1. Google Cloud Run （無料、自動デプロイスクリプト利用）⭐ 最推奨
2. ローカル Docker 運用（開発・テスト用）
3. VPS での Docker 運用
4. ローカルマシンでの直接実行
```

### ⭐ Google Cloud Run （新推奨）

最も簡単な本番運用。まずは以下のガイドを参照：

- Cloud Run 詳細手順: `docs/operations/cloud-run.md`

クイック実行コマンド（参考）：

```bash
./scripts/full-deploy.sh YOUR_PROJECT_ID --with-optional
```

### 基本原則

1. **シンプルさ重視**: 複雑な設定は避ける
2. **環境変数管理**: .env ファイルで設定を一元管理
3. **定期バックアップ**: Obsidian ボルトの定期バックアップ
4. **ログ確認**: 問題発生時のログチェック

## 🐳 ローカル Docker 運用

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
# 自動テストスクリプトで起動
./scripts/docker-local-test.sh

# または手動で起動
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

## 🖥️ VPS 運用

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

## ⚙️ 環境変数設定

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

## 🔧 バックアップとメンテナンス

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

## 📊 監視

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
