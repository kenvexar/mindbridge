# リポジトリ運用ガイドライン（開発者向け）

本ドキュメントは MindBridge への貢献者向けの要約ガイドです。短く確実に、再現性のある作業手順のみを記載します。最短手順は「docs/user/quick-start.md」を参照してください。詳細は各ドキュメントへのリンクを参照してください。

## プロジェクト構成
- `src/` アプリ本体（例: `ai/`, `bot/`, `config/`, `health_analysis/`, `obsidian/`, `tasks/`, `utils/`）
- `tests/` テスト（`unit/`, `integration/`, `manual/`）
- `scripts/` GCP/Secrets/デプロイスクリプト
- `docs/` ユーザー/開発/運用ドキュメント
- 主要エントリ: `python -m src.main`

## ビルド・テスト・開発（クイックリファレンス）
```bash
# セットアップ
uv sync --dev

# 実行（ローカル）
uv run python -m src.main

# テスト / カバレッジ
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing

# Lint / Format / 型
uv run ruff check . --fix && uv run ruff format .
uv run mypy src

# Git フック（pre-commit）
uv run pre-commit run --all-files

# コンテナ（.env.docker を使用）
docker compose up -d
```

## コーディング規約
- 言語: Python 3.13 / インデント 4 スペース / 行長 ~88（ruff 設定）
- 命名: modules/functions `snake_case`、classes `PascalCase`、constants `UPPER_SNAKE_CASE`
- ツール: ruff（lint/format）、mypy（型）、pytest（テスト）
- 公開関数は型注釈を必須（例: `src/ai/vector_store.py`）

## テスト方針
- フレームワーク: pytest（`pyproject.toml` に設定）
- 位置と命名: `tests/unit/test_*.py`、`tests/integration/test_*.py`
- 実行範囲: CI は `unit`/`integration` のみ（`tests/manual/` は収集対象外。必要時に個別実行）
- 目標: 重要ロジックはテスト同伴、カバレッジ目安 80%+
- 外部依存はモック優先（手動検証は `tests/manual/`）

## コミット/PR
- 形式: Conventional Commits（例: `feat: add garmin sync scheduler`、`fix: handle missing discord token`）
- PR 要件:
  - 目的/変更点/影響範囲の簡潔な説明
  - 関連 Issue のリンク（`Closes #123` 等）
  - 動作確認手順・ログ/スクリーンショット（必要時）
- `ruff`, `mypy`, `pytest` を通過済み

## ドキュメントスタイル
- 絵文字は過剰に使用しない（見出し・本文では原則非使用、サンプル出力に限定）
- 見出しは簡潔・用語は一貫（日本語・英語の混在を避ける）
- コマンドやファイルパスはバッククォートで明示（例: `uv run`, `python -m src.main`）

## セキュリティと設定
- 秘密情報は `.env*` に記載し Git へコミットしない（`gitleaks` 等で検知）
- GCP 本番は Secret Manager を利用（`scripts/manage.sh secrets` を参照）
- ローカルは `cp .env.example .env` の上、必要キーを設定

関連: `docs/developer/development-guide.md`, `README.md`, `DEPLOYMENT.md`
