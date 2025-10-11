# Integrations Overview

Garmin と Google Calendar 連携モジュールの要点をコンパクトに整理しました。
詳しい手動テスト手順は `tests/manual/README.md` を参照してください。

## Garmin

- **モジュール**: `src/integrations/garmin/`
- **主なコンポーネント**
  - `GarminClient` (`client.py`): 認証とセッション維持を担当。
  - `GarminSyncService` (`service.py`): 活動データや睡眠ログをフェッチし、
    ライフログへ橋渡し。
  - `cache.py`: Garmin API のレスポンスをローカルキャッシュして、
    レート制限を回避。
- **環境変数**
  - `GARMIN_EMAIL` または `GARMIN_USERNAME`
  - `GARMIN_PASSWORD`
  - `GARMIN_CACHE_DIR`（任意。既定 `/app/.cache/garmin`）
- **実行のヒント**: 初回は `/integration_status` でログイン状態を確認し、
  `/manual_sync` で同期を強制できます。
- **手動テスト**: `uv run python tests/manual/test_garmin_integration.py`

## Google Calendar

- **モジュール**: `src/integrations/google_calendar/`
- **主なコンポーネント**
  - `CalendarSyncService` (`service.py`): OAuth 認証とイベント同期の実体。
  - `schemas.py`: 予定や資格情報の Pydantic モデル。
- **環境変数**
  - `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`
  - `GOOGLE_CALENDAR_ACCESS_TOKEN`, `GOOGLE_CALENDAR_REFRESH_TOKEN`（OAuth 完了後に保存）
  - `GOOGLE_CALENDAR_SERVICE_ACCOUNT`
    （サービスアカウント JSON を base64 で格納する場合）
  - `GOOGLE_CALENDAR_AUTO_DISCOVER` / `GOOGLE_CALENDAR_SYNC_SELECTED_ONLY`
    （任意のブーリアンフラグ）
  - `GOOGLE_CALENDAR_ADDITIONAL_IDS`（カンマ区切りで追加カレンダー ID を指定）
- **実行のヒント**:
  `/integration_config` Slash コマンドで OAuth 認証をトリガーし、
  `/scheduler_status` で同期ジョブを確認できます。
- **手動テスト**: `uv run python tests/manual/test_google_calendar_fix.py`

## 共通ノート

- 設定値は `.env` もしくは Secret Manager からロードされます
  （`SECRET_MANAGER_STRATEGY` を参照）。
- 連携結果は `src/lifelog/` 配下のパイプラインへ渡され、
  Obsidian ノートに反映されます。
- 連携に失敗した場合は `logs/` の最新ファイルと Cloud Logging を確認し、
  必要なら `LOG_LEVEL=DEBUG` で再実行してください。
