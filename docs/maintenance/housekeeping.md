# プロジェクト整理サマリ

継続的なメンテナンス項目、依存関係、推奨コマンドを一覧化しています。ドキュメントと構成の変更履歴をここでトラッキングしてください。

## 1. ディレクトリ構成メモ

- トップレベル構成は「ランタイム (`src/`)」「テスト (`tests/`)」「ドキュメント (`docs/`)」「デプロイ/ツール (`deploy/`, `scripts/`, `docker*`)」「生成物 (`vault/`, `logs/`)」の 5 系統。
- 2025 Q1 のリファクタで `docs/` をカテゴリ別に再編済み（`docs/README.md` をインデックスとして利用）。
- Garmin/Calendar 連携は `src/integrations/` と `src/lifelog/integrations/` に集約済み。旧 `src/garmin/` は互換 API を保持するラッパーとして残置しているため、徐々に `src/integrations/garmin/` へ移行予定。
- `tests/manual/` は用途別スクリプトを配置。必要に応じて README を追加し、外部リソースの前提条件を明示する。
- `logs/`, `vault/` は `.gitkeep` のみコミットし、その他生成物は `./scripts/manage.sh clean` で削除可能。

| パス | 役割 | 現状 | 次のアクション |
| --- | --- | --- | --- |
| `src/ai/`, `src/audio/`, `src/bot/` | AI / 音声 / Discord Bot | README 整備済み。型ヒントとログ共通化済み。 | 新しいワークフロー追加時は README とテストリンクを更新。 |
| `src/integrations/`, `src/lifelog/` | 外部サービス統合 | Integration Manager と Scheduler を共通化。 | 将来的に設定ファイルのスキーマを JSON Schema 化する。 |
| `docs/` | プロジェクトドキュメント | インデックス・クイックスタート・デプロイ・メンテ資料を整理。 | 新しいモジュールが増えたら該当ガイドを追加し、インデックスに追記。 |
| `tests/manual/` | 手動テスト | 音声/ガーミン/管理スクリプトのサンプルを収録。 | テストごとに README を追加し、必要な環境変数を明示。 |
| `scripts/manage.sh` | 管理 CLI | env/secrets/optional/deploy/clean/ar-clean を実装済み。 | 新しい運用タスクを追加する際は同スクリプトへの統合を優先。 |

## 2. 依存関係棚卸し

| 区分 | パッケージ | 用途 / 主な参照箇所 | 備考 |
| --- | --- | --- | --- |
| ランタイム | `discord.py`, `PyNaCl` | Discord Bot / 音声接続 (`src/bot`, `src/audio`) | PyNaCl は音声機能に必須。 |
| ランタイム | `google-genai`, `aiohttp`, `tenacity` | Gemini API 呼び出し (`src/ai`) | モデル更新時は `MODEL_NAME` を変更。 |
| ランタイム | `google-cloud-speech`, `pydub` | Speech-to-Text (`src/audio`) | オプション依存。未設定時はフォールバック動作。 |
| データ処理 | `numpy`, `scikit-learn`, `beautifulsoup4`, `python-dateutil` | ライフログ解析、URL パース、統計処理 | `numpy` と `scikit-learn` は `lifelog` の統計機能で利用。 |
| 設定/セキュリティ | `pydantic`, `pydantic-settings`, `cryptography`, `pyyaml` | 設定管理、Secret 暗号化、YAML 操作 | Secret Manager 暗号化に `Fernet` を使用。 |
| 開発 | `pytest`, `pytest-asyncio`, `mypy`, `ruff`, `pre-commit`, 型スタブ | テスト/静的解析/フォーマッタ | CI で使用するためバージョンを定期的に更新。 |
| 任意 | `google-cloud-secret-manager`, `google-api-python-client` | GCP Secret Manager / Google API 追加連携 | Optional dependencies として `pyproject.toml` に定義。利用時のみ `uv sync --extra ...`。 |

### 更新方針

- 依存を追加する場合は `pyproject.toml` と `docs/maintenance/housekeeping.md` を更新し、利用箇所と理由を明記。
- セキュリティアップデートは `uv run pip-audit --progress-spinner off` で確認し、必要に応じて `scripts/manage.sh` の `clean` → `uv sync --upgrade` を実行。

## 3. ドキュメント整備状況

- 2025 Q1 ドキュメント再編済み: `README.md`（概要・機能・開発手順）、`docs/README.md`（インデックス）、`docs/deploy/cloud-run.md`（Cloud Run 手順）、`docs/basic-usage.md`（コマンド一覧）を更新。
- 未整備項目: `tests/manual/` ごとの README、`src/` 各パッケージの内部ドキュメントの更新頻度向上。
- 追加タスクが発生した際はこのファイルにメモを残し、完了後に履歴として更新。

## 4. 参考コマンド

- キャッシュ/生成物の整理: `./scripts/manage.sh clean --with-uv-cache`
- 依存関係ツリーの確認: `uv pip list --tree`
- 使われていない依存の調査: `rg -g"*.py" "import <pkg>" src tests`
- ドキュメント整合性チェック（リンク確認など）: `rg -g"*.md" "TODO" docs`

## 5. ToDo（随時更新）

- [ ] `src/integrations/` に Garmin/Calendar の README を追加。
- [ ] `tests/manual/` に環境変数サンプルを記載した README を作成。
- [ ] GitHub 同期の設定ガイドを `docs/USER_GUIDE.md` とは別に運用ノートへ切り出すか検討。
