# MindBridge

AI 駆動の知識管理システム。 Discord でメッセージを投稿すると、 AI が自動で Obsidian ノートに整理します。

## 概要

Discord → AI 処理 → Obsidian ノート自動保存。メッセージから自動分類とメタデータ抽出で構造化されたメモ管理。

### 主要機能

AI 駆動メッセージ処理
- AI 分析とメタデータ抽出による自動 Discord メッセージキャプチャ
- URL コンテンツの取得と要約
- インテリジェントな分類とフォルダ割り当て

音声メモ処理
- Google Cloud Speech-to-Text による自動文字起こし
- デプロイ時の自動認証情報生成機能
- 複数の音声フォーマット（ MP3 / WAV / FLAC / OGG / M4A / WEBM ）

Obsidian 統合
- 自動フォルダ分類による構造化 Markdown ノート生成
- Activity Log と Daily Tasks のデイリーノート統合
- プレースホルダー置換に対応したテンプレートシステム

家計管理
- Obsidian 内の収支データモデルと統計表示
- 定期購入サマリーとカテゴリ別集計

タスク管理
- タスク統計（アクティブ件数、完了率など）
- Daily Note との連携による進捗可視化

外部サービス統合
- Garmin Connect ：フィットネス・健康データ同期（ python-garminconnect 使用、 OAuth 不要）
- Google Calendar ：自動イベント・会議インポート
- 健康データ統合：睡眠・歩数・心拍数・アクティビティの自動取得
- GitHub 同期： Obsidian Vault の自動バックアップ
- 暗号化された認証情報ストレージによる安全な認証

## クイックスタート

### ローカル実行（最短 3 ステップ）

```bash
# 1. 依存関係インストール
uv sync --dev

# 2. 環境設定（対話式）
./scripts/manage.sh init

# 3. 起動
uv run python -m src.main
```

### クラウドデプロイ

```bash
# 完全自動デプロイ
./scripts/manage.sh full-deploy YOUR_PROJECT_ID --with-optional

# 基本機能のみ
./scripts/manage.sh full-deploy YOUR_PROJECT_ID
```

### 使用方法

**#memo チャンネルに投稿するだけ！** AI が自動で Obsidian ノートを生成。

## 開発

### 開発クイックリファレンス

```bash
# セットアップ
uv sync --dev

# 実行
uv run python -m src.main

# テスト・品質チェック
uv run pytest -q                                      # テスト実行
uv run pytest --cov=src --cov-report=term-missing    # カバレッジ
uv run ruff check . --fix && uv run ruff format .    # Lint ・ Format
uv run mypy src                                       # 型チェック
uv run pre-commit run --all-files                    # Pre-commit

# コンテナ
docker compose up -d
```

---

**プロジェクト情報**
- Python >=3.13
- MIT ライセンス
