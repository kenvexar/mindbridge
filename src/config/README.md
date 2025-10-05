# Config

## 概要
- アプリケーションの設定値とシークレットを Pydantic で管理します。
- 実行環境ごとの `.env` 読み込みや Secret Manager インターフェースを提供します。

## 主要モジュール
| モジュール | 説明 |
| --- | --- |
| `settings.py` | `.env` / `.env.docker` からロードする基本設定 (`Settings`) |
| `secure_settings.py` | シークレット取得・暗号化ハンドリング (`SecureSettingsManager`) |
| `__init__.py` | `get_settings`, `get_secure_settings` のファサード |

## 外部依存
- `pydantic`, `pydantic-settings`, `python-dotenv`。
- Secret Manager を利用する場合は `google-cloud-secret-manager`。

## テスト
- 設定系の直接テストは未整備。`tests/integration/test_complete_integration.py` や Bot/Audio のテストで間接検証。

## 連携・利用箇所
- `src/main.py` の初期化処理で設定をロードし、各サービスへ注入。
- `scripts/manage.sh` で `.env` を初期生成。

## メモ
- 新しい設定値を追加する際は `Settings` に型定義し、デフォルトと環境変数名を明示。
- Secret Manager 連携を再導入する際は `SecureSettingsManager` の TODO を参照。
