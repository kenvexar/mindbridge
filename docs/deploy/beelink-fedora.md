# Beelink N100 (Fedora 43) 常駐ガイド

Beelink Mini PC (Intel N100) + Fedora 43 で 24/7 稼働させるための手順です。SELinux Enforcing 環境で Docker Compose または systemd + `uv run` のどちらでも動かせます。

## 0. 前提
- OS: Fedora 43 (SELinux Enforcing)
- ユーザー: `mindbridge`（sudo なし推奨）
- 配置先: `/opt/mindbridge`（任意で変更可）

## 1. 必要パッケージ（Docker + uv）
公式リポジトリから Docker Engine と compose plugin を導入します。
```bash
sudo dnf update -y
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin fuse-overlayfs uv
sudo systemctl enable --now docker
```
Docker を一般ユーザーで扱うため、`mindbridge` を `docker` グループに追加して再ログインしてください。
```bash
sudo usermod -aG docker mindbridge
```
Compose のボリュームは `:Z` オプションで SELinux 対応済みです。

## 2. ユーザーとディレクトリ
```bash
sudo useradd -m -s /bin/bash mindbridge || true
sudo mkdir -p /opt/mindbridge
sudo chown -R mindbridge:mindbridge /opt/mindbridge
```

## 3. ソース配置と .env
```bash
sudo -u mindbridge git clone https://github.com/<your-fork>/mindbridge.git /opt/mindbridge
cd /opt/mindbridge
sudo -u mindbridge ./scripts/manage.sh init
sudo -u mindbridge mkdir -p /opt/mindbridge/logs
```
最小構成の `.env` 例:
```env
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
GEMINI_API_KEY=...
OBSIDIAN_VAULT_PATH=/opt/mindbridge/vault
ENVIRONMENT=personal
LOG_LEVEL=INFO
```

## 4A. ホスト実行 (uv) を systemd で常駐
1) 依存同期: `sudo -u mindbridge uv sync --dev`

2) ユニット配置:
```bash
sudo cp deploy/systemd/mindbridge.service /etc/systemd/system/mindbridge.service
# パスを変える場合は sed 等で書き換え
sudo systemctl daemon-reload
sudo systemctl enable --now mindbridge.service
sudo systemctl status mindbridge.service
```

3) ログ確認: `journalctl -u mindbridge.service -f`

## 4B. Docker Compose で常駐（推奨）
```bash
cd /opt/mindbridge
sudo -u mindbridge cp .env .env.docker
sudo -u mindbridge docker compose up -d --build
sudo -u mindbridge docker compose logs -f
```
停止: `docker compose down`

`restart: unless-stopped` が有効なため、ホスト再起動後も Docker デーモン起動と同時に自動再開します。追加の systemd ユニットは不要です。

## 5. ヘルスチェック
- HTTP: `curl http://localhost:8080/health -H "X-Health-Token:<HEALTH_ENDPOINT_TOKEN>"`
- Discord: `/status` Slash コマンドで応答を確認

## 6. バックアップと更新
- Vault/ログは `/opt/mindbridge/{vault,logs,backups}` に置かれるので、ホスト側のバックアップジョブに追加してください。
- 更新時: ホスト実行なら `git pull && uv sync --dev`、Docker なら `docker compose pull && docker compose up -d --build`。

## 7. トラブルシュート
| 症状 | 対応 |
| --- | --- |
| コンテナの Permission denied | SELinux ラベル付きマウント (`:Z`) か、`sudo chown -R mindbridge:mindbridge /opt/mindbridge/{vault,logs,backups,.cache,.config,.mindbridge}` で UID/GID を合わせる |
| ポート 8080 が衝突 | `.env(.docker)` の `PORT` と compose の `ports` を揃えて変更 |
| systemd で `uv` が見つからない | `dnf install uv` 済みか、`which uv` が `/usr/bin/uv` を指すか確認 |

クラウドに頼らず自宅で回したい場合でも、この手順だけで完結します。GPU や追加ストレージを積んだ場合も同じ構成で拡張可能です。
