# Security

## 概要
- シークレット管理、アクセスログ、簡易管理 CLI などセキュリティ関連機能を提供します。
- `BaseSecretManager` を中心に環境変数（Personal）と Google Cloud Secret Manager の両方を扱えるようになりました。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `secret_manager.py` | `BaseSecretManager` 抽象クラス、`PersonalSecretManager`、`GoogleSecretManager`、ファクトリ関数を収録 |
| `access_logger.py` | セキュリティイベントの JSON ログ出力とローテーション |
| `simple_admin.py` | シークレット更新や診断を行う CLI |

## 外部依存
- `structlog`, `aiofiles`, `cryptography`。
- Cloud Secret Manager を利用する場合は `google-cloud-secret-manager`（`uv sync --extra google-api`）が必要。

## テスト
- 単体テスト: `tests/unit/test_security.py`。
- 手動テスト: `tests/manual/test_manage.sh` でシークレット CLI を実行。

## 連携・利用箇所
- `src/main.py` で `log_security_event` を呼び出し、Bot 起動時の監査ログを記録。
- `src/bot/config_manager.py` からシークレット検証に利用。

## メモ
- Secret Manager 再編の詳細は `docs/maintenance/secret-manager-refactor.md` を参照。
- ログファイルの保存先は Settings により切り替え可能。`AccessLogger` が既定で 5 MB × 5 世代でローテーションを自動実行し、`ACCESS_LOG_ROTATION_SIZE_MB` / `ACCESS_LOG_ROTATION_BACKUPS` で調整可能。
