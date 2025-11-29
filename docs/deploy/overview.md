# デプロイ概要

どの環境でどう動かすかを選ぶための比較表と共通フローです。詳細手順は各サブドキュメントへ。

## 戦略別のざっくり比較
| 形態 | 特徴 | コスト/運用 | こんなときに |
| --- | --- | --- | --- |
| ローカル (`uv run`) | 依存は `uv` だけ。コード変更が即反映。 | 無料 / 個人管理 | 開発・デバッグ・お試し運用 |
| Docker/Podman Compose | `.env.docker` とボリュームで環境を固定化。SELinux も `:Z` で対応。 | マシンリソース次第 | チーム共有の検証、簡易常駐 |
| オンプレ (Beelink N100 + Fedora 43) | rootless Podman か systemd + `uv run` で常時稼働。Cloud 依存なし。 | 固定コストのみ / 低運用 | 自宅・個人サーバで 24/7 稼働 |

## どの方式でも共通の流れ
1. 依存同期: `uv sync --dev`
2. シークレット生成: `./scripts/manage.sh init` で `.env` 作成
3. ローカル動作確認: `./scripts/manage.sh run` で Slash コマンドを試す
4. デプロイ: 選んだ方式で `docker compose up` / `podman-compose up` / systemd 常駐
5. ヘルスチェック: `/status`, `/system_status`, `curl localhost:8080/health`
6. 必要なら手動テスト: `tests/manual/` を参照し Vault 出力を確認

## 参考ドキュメント
- ローカル/Docker 手順: `deploy/local.md`
- Beelink + Fedora: `deploy/beelink-fedora.md`
- Vault GitHub 同期やメンテ: `maintenance/github-sync.md`, `maintenance/housekeeping.md`

デプロイ後は Secret 管理とバックアップの状態を定期的に確認し、`/integration_status` で外部連携が生きているかチェックしてください。
