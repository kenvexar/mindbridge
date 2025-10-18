# MindBridge

MindBridge は Discord の会話、添付ファイル、外部連携データを AI で整理し、Obsidian Vault に構造化ノートとして保存する自動化プラットフォームです。ひとつの起動コマンドで要約、タグ付け、統計、バックアップまでを一貫して処理します。

## Core Capabilities
- **Discord ingestion**: メッセージ/添付/埋め込みを取り込み、詳細なメタデータとテキスト整形を実施。
- **AI enrichment**: Gemini 2.5 Flash による要約・タグ・分類、URL 解析、類似ノート参照。
- **Obsidian integration**: テンプレート駆動の Markdown 生成、Daily Note 連携、Vault 統計、GitHub バックアップ。
- **Audio transcription**: Google Cloud Speech-to-Text を優先し、フォールバック保存や使用量監視も実装。
- **Lifelog & health analytics**: Garmin / Google Calendar との同期、活動・睡眠インサイト、自動スケジューラ、ライフログデータ管理。
- **Productivity tooling**: タスク管理、家計管理、定期購入集計、各種 Slash コマンドでの統計表示。
- **Operations & security**: Secret Manager 抽象化、構造化セキュリティログ、軽量ヘルスチェックサーバ、GitHub 同期ワークフロー。

## How It Works
1. **Runtime bootstrap**: `src/main.py` が設定とシークレットを読み込み、AI/Garmin クライアントを遅延初期化。
2. **Discord bot**: `DiscordBot` が Slash コマンドとメッセージハンドラを登録、`MessageProcessor` がメタデータを抽出。
3. **AI & templating**: `AIProcessor`・`AdvancedNoteAnalyzer` が要約やタグを生成し、`TemplateEngine` が YAML フロントマター付きノートを作成。
4. **Vault sync**: `ObsidianFileManager` がノートを保存し、必要に応じて Daily Note へ統合。GitHub 連携がある場合は差分を同期。
5. **Schedulers & integrations**: Garmin/Calendar などは `IntegrationManager` と `HealthAnalysisScheduler` がバックグラウンドで同期。
6. **Monitoring**: `/status` Slash コマンドや HTTP ヘルスサーバが動作状態をレポートし、セキュリティイベントは構造化ログへ記録。

## Quick Start

### Local runtime
```bash
# 1. Install dependencies
uv sync --dev

# 2. Create .env with interactive wizard
./scripts/manage.sh init

# 3. Launch the bridge
./scripts/manage.sh run         # or: uv run python -m src.main
```
Bot を起動したら Discord の #memo チャンネルに投稿し、`/status` で稼働状況を確認してください。

### Cloud Run (summary)
`./scripts/manage.sh full-deploy <PROJECT_ID> --with-optional` で環境セットアップからデプロイまでを自動化できます。詳細は `docs/deploy/cloud-run.md` を参照してください。

### Container image & self-host
```bash
# Build a runnable image (tag freely for GHCR/ECR, etc.)
docker build -t mindbridge:latest .

# Minimal run example for self-hosted VPS
docker run --rm \
  --env-file .env.docker \
  -v "$(pwd)/vault:/app/vault" \
  mindbridge:latest
```
VPS や自前 Kubernetes で運用する場合は上記イメージをレジストリへ push し、
ホスト側で `.env.docker` を管理してください。
Compose や systemd サービス化のヒントは `docs/deploy/local.md` と
`docs/deploy/overview.md` を参照できます。

## Documentation
- ガイドと詳細な手順は `docs/README.md` を参照。
- 使用方法のハイライトは `docs/basic-usage.md`。
- システム構成の概要は `docs/architecture.md`。

## Repository Layout
- `src/` – ドメイン別モジュール (`ai/`, `audio/`, `bot/`, `config/`, `finance/`, `garmin/`, `health_analysis/`, `integrations/`, `lifelog/`, `monitoring/`, `obsidian/`, `security/`, `tasks/`, `utils/`).
- `docs/` – クイックスタート、ユーザーガイド、デプロイ手順、メンテナンスノート。
- `scripts/manage.sh` – 初期化、デプロイ、メンテ、クリーンアップをまとめた CLI。
- `tests/` – `unit/`, `integration/`, `manual/` によるテスト群。
- `deploy/` – Cloud Run・Docker 用のデプロイテンプレート。
- `vault/`, `logs/` – 実行時に生成される Vault と暗号化ログ（Git 管理対象外）。

## Development Checklist
```bash
uv sync --dev
uv run python -m src.main
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check . --fix && uv run ruff format .
uv run mypy src
```
追加のコマンドやメンテナンス手順は `docs/development-guide.md` と `docs/testing.md` を参照してください。

## License

MIT License – 詳細は `LICENSE` を参照。
