# デプロイ概要

MindBridge を運用する代表的なパターンと、ワークフロー全体の流れをまとめます。詳細手順は各サブドキュメントを参照してください。

## デプロイ戦略の比較

| 運用形態 | 特徴 | コスト/運用負荷 | 推奨シナリオ |
| --- | --- | --- | --- |
| ローカル（`uv run`） | 依存関係は `uv` のみ。コード変更が即反映。 | 無料 / 管理者のみ | 開発・デバッグ・検証 |
| ローカル（Docker/Podman Compose） | `docker compose up` で環境再現。Secrets は `.env.docker` を使用。SELinux でも `:Z` で安全。 | マシンリソース次第 | チーム内共有検証、簡易運用 |
| オンプレ（Beelink Mini PC / Fedora 43） | rootless Podman か systemd + `uv run` で常時稼働。Cloud 依存なし。 | 固定コストのみ / 低運用負荷 | 個人常時稼働、宅内サーバー運用 |

## 共通ワークフロー

1. **依存関係同期** – `uv sync --dev`
2. **シークレット初期化** – `./scripts/manage.sh init` で `.env` を作成し必要値を入力
3. **ローカル検証** – `./scripts/manage.sh run` で手動テスト / Slash コマンド確認
4. **デプロイ** – 選択した戦略に応じて `docker compose up` / `podman-compose up` または systemd で常駐化
5. **ヘルスチェック** – `/status`, `/system_status`
6. **手動テスト** – `tests/manual/` のシナリオを必要に応じて実施し、Vault 出力を確認

## GitHub Vault Sync

Vault の GitHub バックアップ手順と必須シークレットは
`docs/maintenance/github-sync.md` に集約しています。重複を避けるため、
環境変数の詳細や運用ノートはそちらを参照してください。

## 参照ドキュメント

- ローカル/Docker 手順: `docs/deploy/local.md`
- Beelink / Fedora 43 手順: `docs/deploy/beelink-fedora.md`
- 継続メンテナンスや構成変更: `docs/maintenance/housekeeping.md`

デプロイ後は GitHub 同期や Secret Manager の状態を定期的に確認し、`/integration_status` や `./scripts/manage.sh clean` など運用コマンドを活用してください。
