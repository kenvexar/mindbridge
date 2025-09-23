# 開発ガイド

## セットアップ

```bash
# 依存関係インストール
uv sync --dev

# 環境設定
./scripts/manage.sh init

# 起動
uv run python -m src.main
```

## 開発フロー

### コード品質

```bash
# Lint & Format
uv run ruff check . --fix && uv run ruff format .

# 型チェック
uv run mypy src

# テスト
uv run pytest -q

# カバレッジ
uv run pytest --cov=src --cov-report=term-missing
```

### Pre-commit

```bash
uv run pre-commit run --all-files
```

## テスト

- `tests/unit/` - 単体テスト
- `tests/integration/` - 統合テスト
- `tests/manual/` - 手動テスト（個別実行）

## アーキテクチャ

- `src/main.py` - エントリーポイント
- `src/bot/` - Discord ボット
- `src/ai/` - AI 処理
- `src/obsidian/` - ファイル管理
- `src/health_analysis/`, `src/lifelog/` - ライフログ
- `src/tasks/`, `src/finance/` - タスク・家計管理
