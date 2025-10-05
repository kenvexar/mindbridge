# Deployment Overview

## デプロイ戦略の比較
| 運用形態 | 特徴 | コスト目安 | 推奨シナリオ |
| --- | --- | --- | --- |
| Google Cloud Run | 24/7 常時稼働・オートスケール・Secret Manager と親和性が高い | 約 8 円/月 （最低構成） | 本番運用・リモートアクセスが必要な場合 |
| ローカル (Docker) | `docker compose` で完結。依存セットアップが容易 | 自宅マシン稼働のみ | 開発検証・短期運用 |
| ローカル (uv run) | 最小構成。コード修正の反映が早い | 0 円 | デバッグ・機能開発 |

## ワークフローの流れ
1. 依存関係の同期: `uv sync --dev`
2. `.env` 初期化: `./scripts/manage.sh init`
3. ローカル確認または Cloud Run へデプロイ
4. ヘルスチェック/手動テスト (`tests/manual/`)

## 関連ドキュメント
- Cloud Run 手順: `docs/deploy/cloud-run.md`
- ローカル運用 / Docker: `docs/deploy/local.md`
- 運用メンテ: `docs/maintenance/housekeeping.md`
