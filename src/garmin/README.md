# Garmin

## 概要
- Garmin Connect API へのアクセスを行う低レベルクライアントとデータ整形処理を提供します。
- 認証、キャッシュ、レスポンスパースを担当し、Lifelog との連携を支えます。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `client.py` | `garminconnect` ライブラリをラップし、非同期操作とリトライを提供 |
| `cache.py` | Garmin データのローカルキャッシュ フォーマット管理 |
| `formatter.py` | Lifelog 取り込み用の辞書データへ整形 |
| `models.py` | Garmin 固有の Pydantic モデル定義 |

## 外部依存
- `garminconnect`, `aiohttp`, `tenacity`, `structlog`。
- 認証情報は環境変数 `GARMIN_EMAIL`/`GARMIN_USERNAME`, `GARMIN_PASSWORD` から取得。

## テスト
- 現時点で専用単体テストは未整備。Garmin フローは `tests/manual/test_garmin_integration.py` で確認。

## 連携・利用箇所
- `src/lifelog/integrations/garmin.py` がこのクライアントを利用してデータを取り込み。
- `src/main.py` の `component_manager` 経由で DI され、Health Scheduler から利用。

## メモ
- `docs/maintenance/integrations-refactor-plan.md` に従い `src/integrations/garmin/` へ移行予定。
- キャッシュディレクトリは `Settings.garmin_cache_dir` で上書き可能。
