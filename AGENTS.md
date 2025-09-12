# Repository Guidelines

本ドキュメントは MindBridge への貢献者向けガイドです。短く確実に、再現性のある作業手順を示します。

## プロジェクト構成
- `src/` アプリ本体（例: `ai/`, `bot/`, `config/`, `health_analysis/`, `obsidian/`, `tasks/`, `utils/`）
- `tests/` テスト（`unit/`, `integration/`, `manual/`）
- `scripts/` GCP/Secrets/デプロイスクリプト
- `docs/` ユーザー/開発/運用ドキュメント
- 主要エントリ: `python -m src.main`

## ビルド・テスト・開発
- セットアップ: `uv sync --dev`
- 実行（ローカル）: `uv run python -m src.main`
- テスト: `uv run pytest -q`
- カバレッジ: `uv run pytest --cov=src --cov-report=term-missing`
- Lint/Format: `uv run ruff check . --fix && uv run ruff format .`
- 型チェック: `uv run mypy src`
- フック: `uv run pre-commit run --all-files`
- コンテナ: `docker compose up -d`（`.env.docker` を使用）

## コーディング規約
- 言語: Python 3.13 / インデント 4 スペース / 行長 ~88（ruff 設定）
- 命名: modules/functions `snake_case`、classes `PascalCase`、constants `UPPER_SNAKE_CASE`
- ツール: ruff（lint/format）、mypy（型）、pytest（テスト）
- 例: `src/ai/vector_store.py` の関数は公開関数に型注釈を必須化

## テスト方針
- フレームワーク: pytest（`pyproject.toml` に設定）
- 位置と命名: `tests/unit/test_*.py`、`tests/integration/test_*.py`
- 目標: 重要ロジックはテスト同伴、カバレッジ目安 80%+
- 外部依存はモック優先（手動検証は `tests/manual/`）

## コミット/PR
- 形式: Conventional Commits（例: `feat: add garmin sync scheduler`、`fix: handle missing discord token`）
- PR 要件:
  - 目的/変更点/影響範囲の簡潔な説明
  - 関連 Issue のリンク（`Closes #123` 等）
  - 動作確認手順・ログ/スクリーンショット（必要時）
  - `ruff`, `mypy`, `pytest` を通過済み

## セキュリティと設定
- 秘密情報は `.env*` に記載し Git へコミットしない（`gitleaks` により検知）
- GCP 本番は Secret Manager を利用（`scripts/setup-secrets.sh` 参照）
- ローカルは `cp .env.example .env` の上、必要キーを設定

補足: 詳細は `docs/developer/development-guide.md` と `README.md` を参照してください。
