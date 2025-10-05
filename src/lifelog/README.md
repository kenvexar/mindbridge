# Lifelog

## 概要
- 日次ライフログの取り込み・整形・保管を担い、Obsidian への書き込みや統合レポート生成を支援します。
- 外部サービス連携のブリッジを提供し、Health Analysis や Tasks と連動します。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `manager.py` | Lifelog 全体の調整役。エントリ作成や構造化を管理 |
| `analyzer.py` | ライフログデータの統計分析（睡眠/活動評価など） |
| `commands.py` | Discord ボットからのライフログ関連指示を処理 |
| `message_handler.py` | Discord メッセージからのログ生成 |
| `integrations/` | Garmin、Google Calendar など外部データを取り込む実装 |
| `models.py` | Lifelog エントリの Pydantic モデル |

## 外部依存
- `structlog`, `numpy`, `scikit-learn`, `aiohttp` (外部連携) 。
- Garmin/Google 連携は `docs/maintenance/integrations-refactor-plan.md` 参照。

## テスト
- 単体テスト: `tests/unit/test_lifelog.py`, `tests/unit/test_daily_integration.py`。
- 手動テスト: `tests/manual/test_garmin_integration.py`, `tests/manual/test_google_calendar_fix.py`。

## 連携・利用箇所
- AI Processor と連携して洞察ノートを生成 (`src/ai/note_analyzer.py`)。
- Obsidian ファイルマネージャへ DI され、日次メモ自動生成 (`src/obsidian/daily_integration.py`)。

## メモ
- 外部連携の責務分離は `src/integrations/` への移行計画に沿って進める。
- スケジューラ連携 (`integrations/scheduler.py`) のリファクタリングが今後の課題。
