# MindBridge

Discord の会話や添付、Garmin / Google Calendar などの外部データを AI で整理し、Obsidian Vault にきれいなノートとして残すワンストップ自動化ツールです。起動しておけば「投稿 → 要約/タグ付け → ノート化 → バックアップ」まで自走します。

## まず動かす 3 手順
1. リポジトリ取得: `git clone https://github.com/<your-org>/mindbridge.git && cd mindbridge`
2. 依存インストール: `uv sync --dev`
3. 環境作成と起動: `./scripts/manage.sh init && ./scripts/manage.sh run`

Discord の監視チャンネルで `/status` が返ってきたら準備完了。必須環境変数は init の対話プロンプトが案内します。

## できること（ざっくり）
- **Discord 取り込み**: 投稿・添付・URL を整形し、メタデータ付きで保存。
- **AI 整理**: Gemini 2.5 Flash で要約・タグ・カテゴリ分類。類似ノート提案も可能。
- **Obsidian 連携**: テンプレート駆動で Markdown 生成、Daily Note 反映、Vault 統計、GitHub 同期。
- **音声メモ**: Google Speech-to-Text で文字起こし。失敗時はファイルのみ保存するフォールバック付き。
- **ライフログ/健康**: Garmin・Calendar を同期し、睡眠/活動インサイトを日次ノートに追加。
- **タスク/家計**: Slash コマンドでタスクや支出を登録し、集計を返答。
- **運用機能**: Secret Manager 抽象化、構造化セキュリティログ、軽量ヘルスサーバ。

## 動きの流れ
1. `src/main.py` が設定とシークレットを読み込み、Discord Bot と外部連携を初期化。
2. 投稿を `MessageProcessor` が整形し、`AIProcessor` / `AdvancedNoteAnalyzer` が要約とタグ付け。
3. `TemplateEngine` が YAML フロントマター付き Markdown を生成し、`ObsidianFileManager` が Vault に保存。
4. `DailyNoteIntegration` や各スケジューラが Garmin / Calendar / GitHub 同期をバックグラウンドで処理。
5. `/status` や HTTP ヘルスエンドポイントが稼働状況を返し、セキュリティイベントは構造化ログに残ります。

## デプロイの選択肢
- **ローカル実行 (`uv run`)**: 最軽量。コード変更が即反映。開発・個人運用向け。
- **Docker / Podman Compose**: `.env.docker` とボリュームで環境を固定化。チーム検証や自宅サーバに便利。
- **Beelink N100 + Fedora 43**: `docs/deploy/beelink-fedora.md` に常駐手順を記載（SELinux/Podman/systemd 対応）。

コンテナイメージが必要なら `docker build -t mindbridge:latest .` で作成し、`.env.docker` と `vault` をマウントしてください。詳しくは `docs/deploy/local.md` / `docs/deploy/overview.md`。

## ドキュメントへの入口
- インデックス: `docs/README.md`
- すぐ使う: `docs/quick-start.md`
- コマンド一覧: `docs/basic-usage.md`
- 仕組み: `docs/architecture.md`
- 開発・テスト: `docs/development-guide.md`, `docs/testing.md`

## リポジトリの見取り図
- `src/` – AI・Bot・Obsidian・Integrations ほかのドメイン別モジュール
- `docs/` – クイックスタート、ユーザーガイド、デプロイ、メンテ資料
- `scripts/manage.sh` – 初期化/起動/掃除/デプロイをまとめた CLI
- `tests/` – `unit/`, `integration/`, `manual/`
- `deploy/` – Docker・systemd テンプレート
- `vault/`, `logs/` – 実行時に生成されるデータ（Git 管理対象外）

## 開発時によく使うコマンド
```bash
uv sync --dev
uv run python -m src.main
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check . --fix && uv run ruff format .
uv run mypy src
```
追加のフローやヒントは `docs/development-guide.md` と `docs/testing.md` を参照してください。

## License
MIT License（詳細は `LICENSE` を参照）。
