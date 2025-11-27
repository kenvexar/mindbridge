# 開発ガイド

ローカル開発やレビュー時に実施する手順とコマンドをまとめています。スタイル・テスト要件は `AGENTS.md` と `project-doc` のガイドラインに従ってください。

## セットアップ

```bash
# 依存関係と開発用ツールを取得
uv sync --dev

# .env を対話式に生成（必要なシークレットを登録）
./scripts/manage.sh init

# Bot をローカル起動して挙動を確認
./scripts/manage.sh run        # もしくは: uv run python -m src.main
```

`./scripts/manage.sh` は初期化・デプロイ・クリーンアップを集約した CLI です。コマンド一覧は `./scripts/manage.sh help` で確認できます。

## 日常作業フロー

1. ブランチ作成後、目的の修正を実装。
2. 必要に応じて手動テスト（Discord での Slash コマンド、Garmin/Calendar 同期など）を実行。
3. 変更内容に対して以下の品質チェックを実施。

```bash
# Lint と自動整形
uv run ruff check . --fix
uv run ruff format .

# 型チェック
uv run mypy src

# 単体・統合テスト
uv run pytest -q

# カバレッジ（新規ロジックを追加した場合）
uv run pytest --cov=src --cov-report=term-missing

# Pre-commit（コミット直前）
uv run pre-commit run --all-files
```

> `ruff` の最大行長は 88 文字です。`ruff format` を実行すると PEP 621/pyproject の設定に従って整形されます。

## テスト構成

- `tests/unit/` – ドメイン別の単体テスト。モックやフィクスチャは `tests/conftest.py` に集約。
- `tests/integration/` – Discord モック、AI 処理、Obsidian ファイル操作など複数ドメインを跨る検証。
- `tests/manual/` – 音声処理・Garmin・管理スクリプトなど外部リソースを必要とするチェック。必要な場合のみ手動で実行。

テストコマンド例:

```bash
uv run pytest tests/unit/test_ai_processor.py        # 個別テスト
uv run pytest tests/integration -k garmin            # Garmin 関連のみ
uv run python tests/manual/quick_voice_test.py       # 手動音声テスト
```

## 管理スクリプトの活用

- `./scripts/manage.sh clean` – `__pycache__`, `.pytest_cache`, `.ruff_cache` などを削除。`--with-uv-cache` フラグで `~/.cache/uv` も削除可能。
- `./scripts/manage.sh secrets <PROJECT_ID>` – Secret Manager へのシークレット登録。

新しいタスクを追加する場合は既存のサブコマンドを調べ、可能なら同スクリプトに統合してください。

## 主要ディレクトリのおさらい

| ディレクトリ | 説明 |
| --- | --- |
| `src/ai/` | Gemini クライアント、AIProcessor、URL/ベクターストア処理。 |
| `src/bot/` | Discord Bot クライアント、Slash コマンド、メッセージハンドラ。 |
| `src/obsidian/` | Vault への書き込み、テンプレート、統計、GitHub 同期。 |
| `src/lifelog/`, `src/integrations/`, `src/health_analysis/` | Garmin / Calendar / ライフログ統合とスケジューラ。 |
| `src/tasks/`, `src/finance/` | タスク・家計管理モジュールと Slash コマンド。 |
| `src/security/`, `src/monitoring/` | Secret Manager 抽象化、アクセスログ、ヘルスチェックサーバ。 |

モジュール単位のより詳細な説明は各 `src/<package>/README.md` を参照してください。

## コードスタイルとガイドライン

- Python は 4 スペースインデント、公開 API には型ヒント必須。
- 変数/関数はスネークケース、Discord のイベントハンドラなどフレームワーク要件がある場合のみ camelCase を使用。
- ログには `structlog` を用い、機密データを出力しないよう `secure_log_message_content` などのヘルパーを活用。
- コメントは複雑な処理や注意点に限定し、冗長な説明は避ける。
- コミットは Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`...) に従い、72 文字以内の命令形サマリを使用。

## よく使う補助コマンド

```bash
uv run pip-audit --progress-spinner off    # 依存性の脆弱性チェック
uv run python -m src.main --help           # 起動オプションの確認
rg --files docs                            # ドキュメント一覧の確認
rg "TODO" -g"*.py" src                     # TODO の洗い出し
```

開発フローを終えたら、`docs/testing.md` に記載のテスト実施状況を PR などで共有してください。
