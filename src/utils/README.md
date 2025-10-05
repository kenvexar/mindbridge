# Utils

## 概要
- ロギング、DI、キャッシュ、エラーハンドリングなど、全体で共有するユーティリティをまとめています。
- 直接的なビジネスロジックは含まず、各パッケージのインフラ層を支えます。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `logger.py` | `structlog` と `rich` によるロギング設定・ヘルパー |
| `lazy_loader.py` | 遅延初期化とシングルトン管理 (`component_manager`) |
| `mixins.py` | ロガーや設定取得の共通 Mixin |
| `error_handler.py` | 例外整形と通知処理 |
| `lru_cache.py` | シンプルな LRU キャッシュ実装 |
| `mcp_client.py` | Model Context Protocol クライアントラッパー |
| `memory_manager.py` | ローカルファイルベースのメモリ記録 |

## 外部依存
- `structlog`, `rich`, `aiofiles` (一部), `typing-extensions`。

## テスト
- 単体テスト: `tests/unit/test_utils.py`。
- その他のパッケージテストからも間接的に使用。

## 連携・利用箇所
- `src/main.py` の `setup_logging` を通じて全体のロギング設定を初期化。
- 各サービスが `LoggerMixin` を継承しロギングを統一。

## メモ
- `component_manager` に登録する新規サービスは README を更新し、DI 設計を共有する。
- CLI からの利用例は `docs/maintenance/housekeeping.md` 参照。
