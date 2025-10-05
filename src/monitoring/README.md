# Monitoring

## 概要
- ランタイムのヘルスチェックやメトリクス公開を行う軽量 HTTP サーバを提供します。
- Cloud Run デプロイ時の稼働監視エンドポイントとして利用されます。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `health_server.py` | `HealthServer` 実装。`aiohttp` ベースで `/health` を提供 |

## 外部依存
- `aiohttp`, `cryptography` (ヘルスエンドポイントでの署名検証に使用)。

## テスト
- 専用テストは未整備。`tests/integration/test_complete_integration.py` の起動シーケンスで暗黙的に確認。

## 連携・利用箇所
- `src/main.py` の `RuntimeContext` に組み込まれ、Bot 起動と同時に開始。
- `scripts/manage.sh deploy` のヘルスチェックで呼び出される。

## メモ
- 今後 Prometheus 互換メトリクスへ拡張する場合は `aiohttp` のミドルウェア追加を検討。
