# 開発ガイド

ローカル開発やレビューで迷わないための最小セットです。詳細なポリシーはルートの `AGENTS.md` を参照してください。

## 1. いつもの起動手順
```bash
uv sync --dev              # 依存と開発ツール
./scripts/manage.sh init   # .env を対話生成（初回のみ）
./scripts/manage.sh run    # Bot 起動
```
`./scripts/manage.sh help` でサブコマンド一覧を確認できます。

## 2. 変更後に回すチェック
```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy src
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing   # 新規ロジックを追加したとき
uv run pre-commit run --all-files                   # コミット直前
```
`ruff` の行長は 88 文字。CI も同じ設定です。

## 3. テストの粒度
- `tests/unit/` — ドメイン単位のテスト。モックやフィクスチャは `tests/conftest.py` に集約。
- `tests/integration/` — Discord モック、AI、ファイル操作を跨る検証。
- `tests/manual/` — 外部サービスや音声など、手動で走らせるチェック。

例:
```bash
uv run pytest tests/unit/test_ai_processor.py
uv run pytest tests/integration -k garmin
uv run python tests/manual/quick_voice_test.py
```

## 4. 管理スクリプトの便利機能
- `./scripts/manage.sh clean` — キャッシュ削除（`--with-uv-cache` で uv キャッシュも削除）
- `./scripts/manage.sh run --once` — 短時間だけ起動したいときに便利

新しい運用タスクは可能な限りこのスクリプトに統合してください。

## 5. ディレクトリ早見表
| パス | 役割 |
| --- | --- |
| `src/ai/` | Gemini クライアント、AIProcessor、URL/ベクターストア処理 |
| `src/bot/` | Discord Bot クライアント、Slash コマンド、メッセージハンドラ |
| `src/obsidian/` | Vault 書き込み、テンプレート、統計、GitHub 同期 |
| `src/integrations/`, `src/lifelog/`, `src/health_analysis/` | Garmin / Calendar / 健康分析、Scheduler |
| `src/tasks/`, `src/finance/` | タスク・家計管理モジュール |
| `src/security/`, `src/monitoring/` | アクセスログとヘルスチェックサーバ |

## 6. コーディングの心得
- 4 スペースインデント、公開 API には型ヒント必須。
- 変数/関数は snake_case（Discord の callback 要件のみ camelCase）。
- ログは機密を含めないようヘルパーを利用し、必要ならセキュリティログへ出力。
- コメントは複雑な箇所だけに短く付ける。冗長な説明は避ける。
- コミットメッセージは Conventional Commits 形式で 72 文字以内。

## 7. よく使う補助コマンド
```bash
uv run pip-audit --progress-spinner off   # 依存脆弱性チェック
uv run python -m src.main --help          # 起動オプション確認
rg --files docs                           # ドキュメント一覧
rg "TODO" -g"*.py" src                   # TODO の洗い出し
```

テストの実施状況やカバレッジは PR の Verification セクションに記載してください。
