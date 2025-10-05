# Secret Manager Abstraction

## 目的
- 個人利用 (環境変数) と Google Cloud Secret Manager の両対応を可能にする。
- 将来的に他のキーバックエンド (HashiCorp Vault など) を追加しやすくする。

## 実装概要
- `src/security/secret_manager.py`
  - `BaseSecretManager`: キャッシュ処理と共通ログを担う抽象基底クラス。
  - `PersonalSecretManager`: 環境変数を利用する既存実装。`BaseSecretManager` 継承に切り替え。
  - `GoogleSecretManager`: `google-cloud-secret-manager` を利用する新実装。任意の AsyncClient を DI 可能。
  - `ConfigManager`: Secret Manager を受け取り、`get_config_value` を共通化。
  - `create_secret_manager` / `create_config_manager`: デプロイ戦略からクラスを生成するファクトリ。
- `src/security/__init__.py`: 新しい API を公開。
- `tests/unit/test_security.py`: Google Secret Manager の挙動とファクトリを検証するテストを追加。

## 導入方法
- Cloud Run 等で使用する場合: `create_secret_manager("google", project_id=...)` を呼び出し、得られたインスタンスを `ConfigManager` に渡す。
- 個人環境では従来通り `PersonalConfigManager` を利用すれば自動的に `PersonalSecretManager` が採用される。
