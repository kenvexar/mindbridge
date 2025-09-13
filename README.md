# MindBridge

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**AI 駆動知識管理システム** - Discord をインターフェースとして使用し、インテリジェントなメモ処理と自動 Obsidian ノート保存を行います。

## 概要

MindBridge は知識管理システムです。 Discord サーバーでメッセージをキャプチャし、 Google Gemini AI で処理して、自動分類とメタデータ抽出により構造化された Obsidian ノートに整理します。

### 主要機能

**🤖 AI 駆動メッセージ処理**
- AI 分析とメタデータ抽出による自動 Discord メッセージキャプチャ
- URL コンテンツの取得と要約
- インテリジェントな分類とフォルダ割り当て

**🎤 音声メモ処理**
- Google Cloud Speech-to-Text による自動文字起こし
- デプロイ時の自動認証情報生成機能
- 複数の音声フォーマットサポート（ MP3 、 WAV 、 FLAC 、 OGG 、 M4A 、 WEBM ）
- 60 分/月の無料枠内で利用可能

**📝 Obsidian 統合**
- 自動フォルダ分類による構造化 Markdown ノート生成
- Activity Log と Daily Tasks との Daily Note 統合
- プレースホルダー置換機能付きテンプレートシステム

**💰 家計管理**
- 支出追跡とサブスクリプション管理
- 自動財務レポートと予算管理

**✅ タスク管理**
- タスクの作成、追跡、生産性レビュー
- 進捗追跡機能付きプロジェクト管理

**🔗 外部サービス統合**
- **Garmin Connect**：フィットネスと健康データ同期（ python-garminconnect 使用、 OAuth 不要）
- **Google Calendar**：自動イベントと会議インポート
- **健康データ統合**：睡眠・歩数・心拍数・アクティビティの自動取得
- **GitHub 同期**： Obsidian vault の自動バックアップ
- 暗号化された認証情報ストレージによる安全な認証

## クイックスタート

### 🧑‍💻 ローカル（最短）

```
uv sync --dev
./scripts/manage.sh init   # 対話で .env を生成
uv run python -m src.main      # もしくは ./scripts/manage.sh run
```

詳細: docs/user/quick-start.md

### 🚀 Google Cloud Run デプロイ（推奨）

**完全自動デプロイスクリプト**で 5 分でデプロイ完了：

```bash
# リポジトリをクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 完全自動デプロイ（推奨）
./scripts/manage.sh full-deploy YOUR_PROJECT_ID --with-optional

# 基本機能のみデプロイ
./scripts/manage.sh full-deploy YOUR_PROJECT_ID
```

**特徴**：
- ✅ Google Cloud 環境の自動セットアップ
- ✅ Speech-to-Text 認証情報の自動生成
- ✅ Garmin Connect 統合（ OAuth 不要）
- ✅ GitHub 同期による無料永続化
- ✅ エラー処理とリトライ機能

### 💻 ローカル開発

```bash
# 依存関係をインストール
uv sync

# 環境設定
cp .env.example .env
# API キーで .env ファイルを編集

# ボットを開始 / デバッグ
uv run python -m src.main
uv run python -m src.main --debug  # 任意
```

### 使用方法

**#memo チャンネルに投稿するだけ！** AI が自動的に Obsidian ノートを生成し、適切なフォルダに分類します。

詳細な使用方法と AI 分類システムは [基本的な使用方法](docs/user/basic-usage.md) を参照してください。

## 開発

詳細な開発コマンドとアーキテクチャについては [開発ガイド](docs/developer/development-guide.md) を参照してください。

### 開発クイックリファレンス

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

# フック（pre-commit）
uv run pre-commit run --all-files

# コンテナ
docker compose up -d
```

#### Manual Tests（任意実行）

CI 対象外の手動テストは必要時に個別実行してください：

- 音声テスト（簡易）: `uv run python tests/manual/quick_voice_test.py`
- 実音声テスト: `uv run python tests/manual/test_real_voice.py`
- 音声メモ総合: `uv run python tests/manual/test_voice_memo.py`
- Garmin 統合: `uv run python tests/manual/test_garmin_integration.py`
- CLI 動作検証: `bash tests/manual/test_manage.sh`

より詳細な運用ルールは [リポジトリ運用ガイドライン](docs/developer/repository-guidelines.md) を参照してください。

## ドキュメント

### 📚 ユーザードキュメント
- **[クイックスタート](docs/user/quick-start.md)** - 最短 3 ステップ
- **[インストールガイド](docs/user/installation.md)** - 全機能の詳細手順
- **[基本的な使用方法](docs/user/basic-usage.md)** - 日常の使用方法
- **[コマンドリファレンス](docs/user/commands-reference.md)** - 利用可能なコマンド
- **[使用例](docs/user/examples.md)** - 使用例
- **[Vault 移行ガイド](docs/user/vault-migration.md)** - 既存 Obsidian Vault からの移行

### 🛠️ 開発者ドキュメント
- **[開発ガイド](docs/developer/development-guide.md)** - 開発環境セットアップ
- **[アーキテクチャ](docs/developer/architecture.md)** - システム設計
- **[API ドキュメント](docs/developer/api-documentation.md)** - API リファレンス
- **[YAML フロントマターシステム](docs/developer/yaml-frontmatter-system.md)** - テンプレートシステム
- **[フィールドリファレンス](docs/developer/field-reference.md)** - データフィールド仕様

### 🚀 運用ドキュメント
- **[デプロイメント](docs/operations/deployment.md)** - 本番デプロイメント（全体像）
- **[Cloud Run デプロイ](docs/operations/cloud-run.md)** - 具体的な Cloud Run 手順
- **[GCP デプロイメント](docs/operations/gcp-deployment.md)** - Google Cloud Platform デプロイ
- **[監視](docs/operations/monitoring.md)** - 監視とログ
- **[トラブルシューティング](docs/operations/troubleshooting.md)** - 問題解決

## サポート環境

- **開発**：モックモードサポート付きローカル開発
- **運用**：ローカルまたは VPS での 24/7 運用
- **コンテナ**： Docker サポート
- **OS**： macOS 、 Linux 、 Windows （ WSL2 ）

## 貢献

貢献歓迎！貢献ガイドラインについては開発ガイドを参照してください。

## ライセンス

MIT ライセンス - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## サポート

- **Issues**：[GitHub Issues](https://github.com/kenvexar/mindbridge/issues) でバグ報告と機能要求
- **ドキュメント**：包括的なドキュメントが利用可能
  - [外部統合ガイド](docs/integrations/external-integrations.md) - Garmin 、 Google Calendar 、金融データ統合
  - [Garmin 統合ガイド](docs/integrations/garmin-integration.md) - Garmin Connect の詳細設定
- **ディスカッション**：プロジェクトディスカッションとコミュニティサポート

---

**プロジェクト情報**
- バージョン管理：`src/__init__.py` の `__version__` を参照
- Python：3.13+
- 最終更新：2025
