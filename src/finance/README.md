# Finance

## 概要
- サブスクリプションや支出の記録、定期的なリマインド通知を行う個人向け家計管理機能を提供します。
- Obsidian ノートや Discord 通知と連携し、収支サマリを生成します。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `expense_manager.py` | 支出・収入の CRUD とファイル保存 (`aiofiles`) |
| `subscription_manager.py` | サブスクリプション契約の管理と更新通知 |
| `budget_manager.py` | 予算カテゴリと進捗のトラッキング |
| `report_generator.py` | 月次レポートの生成 |
| `reminder_system.py` | Discord への支払いリマインド |
| `message_handler.py` | Bot からの指示をハンドリング |

## 外部依存
- `aiofiles`, `structlog`, `python-dateutil`。
- Discord 送信は Bot の通知システムを利用するため、追加の API キーは不要。

## テスト
- 直接の単体テストは未整備。主要フローは `tests/manual/test_manage.sh` からの操作や統合テストで確認予定。

## 連携・利用箇所
- `src/bot/commands/finance_commands.py` から呼び出され、正規化された支出データを扱う。
- Obsidian ファイルマネージャと連携し、ノートへ月次レポートを出力。

## メモ
- データファイルは JSON/YAML を使用。Vault へのバックアップを検討。
- 今後 `pandas` ベースの分析を導入する場合は依存追加判断が必要。
