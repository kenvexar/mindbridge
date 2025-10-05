# Bot

## 概要
- Discord Bot のエントリポイント、Slash コマンド群、イベントハンドラをまとめた中核パッケージです。
- AI 処理、タスク管理、Obsidian 連携など各ドメインサービスへのゲートウェイ役を果たします。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `client.py` | `discord.py` をベースにした Bot クライアント初期化 |
| `commands/` | タスク、統計、設定などの Slash コマンド実装 |
| `handlers/` | メッセージ・ファイル・音声などのイベント処理 |
| `message_processor.py` | 受信メッセージを解析し AI/Obsidian へルーティング |
| `config_manager.py` | ボット設定・認証情報の検証および Secret Manager 連携 |
| `metrics.py` | API 利用状況とレート管理の集計 |

## 外部依存
- `discord.py`, `aiohttp`, `structlog`, `aiofiles`。
- 必須シークレット: `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID` (任意) 。

## テスト
- 単体テスト: `tests/unit/test_handlers.py`, `tests/unit/test_utils.py`。
- 統合テスト: `tests/integration/test_complete_integration.py`。
- 手動テスト: `tests/manual/test_manage.sh` で CLI 操作確認。

## 連携・利用箇所
- `src/main.py` で DI され、AI や Obsidian、Tasks のサービスを注入。
- 監視サーバ (`src/monitoring/health_server.py`) から稼働状態チェックが呼ばれる。

## メモ
- コマンド追加時は `commands/__init__.py` の登録と `tests/unit/test_handlers.py` の更新を忘れずに。
- トークン検証は `ConfigManager.validate_api_key` を通じて共通化済み。
