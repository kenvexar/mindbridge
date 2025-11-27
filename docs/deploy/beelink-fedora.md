# Beelink Mini PC (N100, Fedora 43) デプロイガイド

Cloud Run ではなく、Beelink 製 Mini PC (Intel N100 / Alder Lake) 上で常時稼働させるための手順です。Fedora 43 + SELinux Enforcing を想定し、パッケージは `dnf` と rootless Podman を利用します。

## 0. 前提

- OS: Fedora 43 (SELinux Enforcing)
- ハードウェア: Beelink Mini PC N100（x86_64）
- 実行ユーザー: `mindbridge`（推奨、sudo なし）
- レポジトリ配置: `/opt/mindbridge`（任意で変更可）

## 1. 依存パッケージ

```bash
sudo dnf update -y
sudo dnf install -y git curl podman podman-docker podman-compose fuse-overlayfs
# Python ツールチェーン（後でサービスユーザーにもインストール）
pipx install uv
pipx ensurepath  # 未設定なら shell を再起動
```

SELinux でコンテナボリュームのラベル付けを行うため `:Z` オプションを付けてマウントします（`docker-compose.yml` を更新済み）。

## 2. ユーザーとディレクトリ

```bash
sudo useradd -m -s /bin/bash mindbridge || true
sudo mkdir -p /opt/mindbridge
sudo chown -R mindbridge:mindbridge /opt/mindbridge

# mindbridge ユーザーに uv をインストール（systemd もこの PATH を使う）
sudo -u mindbridge pipx install uv
sudo -u mindbridge pipx ensurepath
```

## 3. ソース配置と環境変数

```bash
sudo -u mindbridge git clone https://github.com/<your-fork>/mindbridge.git /opt/mindbridge
cd /opt/mindbridge
sudo -u mindbridge ./scripts/manage.sh init   # .env を対話生成（SECRET_MANAGER_STRATEGY=env を維持）
```

### `.env` 最低限の例

```env
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
GEMINI_API_KEY=...
OBSIDIAN_VAULT_PATH=/opt/mindbridge/vault
SECRET_MANAGER_STRATEGY=env
ENVIRONMENT=personal
LOG_LEVEL=INFO
```

## 4A. ホスト実行 (uv) + systemd 常駐

1) 依存同期

```bash
sudo -u mindbridge uv sync --dev
```

2) systemd ユニットを配置

`deploy/systemd/mindbridge.service` を環境に合わせて修正し、以下で導入します。

```bash
sudo cp deploy/systemd/mindbridge.service /etc/systemd/system/mindbridge.service
sudo sed -i 's#/opt/mindbridge#/opt/mindbridge#g' /etc/systemd/system/mindbridge.service  # パスを変更する場合のみ
# uv を pipx で入れた場合は PATH 行が /home/mindbridge/.local/bin を含むことを確認
sudo systemctl daemon-reload
sudo systemctl enable --now mindbridge.service
sudo systemctl status mindbridge.service
```

3) ログ確認

```bash
journalctl -u mindbridge.service -f
```

## 4B. Podman Compose 実行 (推奨: SELinux 対応)

```bash
cd /opt/mindbridge
sudo -u mindbridge cp .env .env.docker
sudo -u mindbridge podman-compose up -d --build
sudo -u mindbridge podman-compose logs -f
```

停止は `podman-compose down`。自動起動させる場合は以下で systemd ユニットを生成できます。

```bash
sudo -u mindbridge podman generate systemd --name personal-mindbridge --files --new
sudo cp personal-mindbridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now personal-mindbridge.service
```

## 5. ヘルスチェック

- HTTP: `curl http://localhost:8080/health -H "X-Health-Token:<HEALTH_ENDPOINT_TOKEN>"`
- Discord: `/status` Slash コマンドで起動確認

## 6. バックアップと更新

- Vault やログは `/opt/mindbridge/{vault,logs,backups}` に保存されるため、ホスト側のバックアップジョブに追加してください。
- アップデート時は `git pull && uv sync --dev`（ホスト実行）または `podman-compose pull && podman-compose up -d --build` を実行します。

## 7. トラブルシューティング

| 症状 | 対応 |
| --- | --- |
| コンテナ起動時に Permission denied | SELinux が原因のため `:Z` 付きボリュームがマウントされているか確認。`podman unshare chown` で UID/GID を合わせると解決する場合があります。 |
| ポート 8080 が衝突 | `.env(.docker)` で `PORT` を変更し、`docker-compose.yml` の `ports` も合わせて更新。 |
| systemd で uv が見つからない | mindbridge ユーザーで `pipx install uv` 済みか確認し、`Environment=PATH=/home/mindbridge/.local/bin:/usr/local/bin:/usr/bin` をユニットで調整。 |

---

Fedora 43 上で Cloud Run 依存を排し、ローカルだけで完結する構成です。追加のストレージや GPU を搭載した場合も同じ手順で拡張できます。
