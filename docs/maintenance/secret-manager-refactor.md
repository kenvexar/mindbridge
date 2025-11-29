# Secret Manager 抽象化メモ

環境変数だけで動かす個人利用と、Google Cloud Secret Manager を使う運用の両方を支えるための設計ノートです。

## ゴール
- バックエンドを差し替えても呼び出し側のコードをほぼ変えずに済むこと。
- 将来 HashiCorp Vault など別ストアを増やすときの足場を作ること。

## 実装ポイント
- `src/security/secret_manager.py`
  - `BaseSecretManager`: キャッシュと共通ログを持つ抽象基底。
  - `PersonalSecretManager`: 環境変数ベース。既存実装を継承に置き換え。
  - `GoogleSecretManager`: `google-cloud-secret-manager` をラップ。AsyncClient を DI 可能。
  - `ConfigManager`: Secret Manager 経由で設定値を取得する共通窓口。
  - `create_secret_manager` / `create_config_manager`: デプロイ戦略に応じてインスタンスを生成するファクトリ。
- `src/security/__init__.py`: 新 API の公開場所。
- `tests/unit/test_security.py`: Google Secret Manager 振る舞いとファクトリの回帰テスト。

## 使い方の早見
- GCP Secret Manager を使う: `create_secret_manager("google", project_id=...)` を呼び、その結果を `ConfigManager` に渡す。
- 個人環境（env only）: これまで通り `PersonalConfigManager` を使えば内部で `PersonalSecretManager` が選ばれる。

この方針に沿って新しいバックエンドを追加する場合は、`BaseSecretManager` を継承してキャッシュ・ログの扱いを揃えること。
