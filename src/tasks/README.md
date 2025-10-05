# Tasks

## 概要
- 個人タスクの登録・進捗管理・リマインドを統合し、Obsidian ノートと Discord 通知に同期します。
- スケジュール化されたタスクの実行や日次レポート生成を提供します。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `task_manager.py` | タスクデータの CRUD、状態遷移、ファイル保存 |
| `schedule_manager.py` | タスクスケジュールとリマインダー生成 |
| `commands.py` | Discord Slash コマンドの実装 |
| `report_generator.py` | タスク進捗のサマリーレポート生成 |
| `reminder_system.py` | Discord 通知や Obsidian へのリマインド出力 |
| `models.py` | タスク/プロジェクトの Pydantic モデル |

## 外部依存
- `aiofiles`, `structlog`, `python-dateutil`。

## テスト
- 単体テスト: `tests/unit/test_handlers.py`（コマンド連携）, `tests/unit/test_utils.py`（共通ヘルパー）。
- 手動テスト: `tests/manual/test_manage.sh` にタスク操作のシナリオあり。

## 連携・利用箇所
- `src/bot/commands/task_commands.py` や `src/bot/handlers` から呼び出され、タスクデータを同期。
- 日次ノート統合 (`src/obsidian/daily_integration.py`) でタスク完了状況を集約。

## メモ
- ステータスアイコンの定義は `TaskStatus` と一致させること。
- 今後カレンダー連携を追加する場合は `docs/maintenance/integrations-refactor-plan.md` のパッケージ設計を参照。
