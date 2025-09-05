# MindBridge

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

AI 駆動の個人ナレッジブリッジ - Discord と Obsidian を繋ぎ、思考を知識に変換

## 概要

MindBridge は、Discord を統合インターフェースとして使用し、AI 分析による自動メモ処理と Obsidian ナレッジベースへの保存を提供する AI 駆動の個人ナレッジブリッジシステムです。

### 主要機能

🤖 **AI 駆動の自動処理**
- Google Gemini AI によるメッセージの自動分析・分類・要約
- URL コンテンツの自動取得と要約
- インテリジェントなタグ付けとカテゴリ分類

🎤 **音声メモ対応**
- Google Cloud Speech-to-Text による高精度音声認識
- 複数音声フォーマット対応（ MP3, WAV, FLAC, OGG, M4A, WEBM ）

📝 **Obsidian 完全統合**
- 構造化 Markdown ノートの自動生成
- 内容に基づく自動フォルダ分類
- デイリーノートとの統合
- 柔軟なテンプレートシステム

💰 **金融管理機能**
- 支出・収入の自動記録と分類
- 定期購入（サブスクリプション）管理
- 自動家計レポート生成

✅ **タスク・プロジェクト管理**
- メッセージからのタスク自動抽出
- プロジェクト進捗追跡
- 生産性レビューの自動生成

🏃‍♂️ **健康データ統合**（オプション）
- Garmin Connect 統合による活動データ同期
- 睡眠・運動パターンの分析

## クイックスタート

### 1. 前提条件
- Python 3.13 以上
- [uv](https://github.com/astral-sh/uv) （高速 Python パッケージマネージャー）
- Discord Bot トークン
- Google Gemini API キー
- Obsidian ボルト

### 2. インストール
```bash
# リポジトリのクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 依存関係のインストール
uv sync

# 環境設定
cp .env.example .env
# .env ファイルを編集して API キーを設定
```

### 3. 基本設定

```env
# 必須設定項目のみ
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_guild_id
GEMINI_API_KEY=your_gemini_api_key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

**それだけです！** チャンネル ID の設定は不要です。

### 4. 起動
```bash
uv run python -m src.main
```

### 5. Discord チャンネル作成（ 2025 年大幅簡素化）

**必須チャンネル（ 3 つのみ）：**
```
📝 memo           ← 統合メイン入力（必須）- テキスト・音声・ファイル全て統合
🔔 notifications  ← システム通知（必須）
🤖 commands       ← ボットコマンド（必須）
```

**🎯 大幅簡素化： 3 チャンネルのみ**
- 旧システム： 17+の専用チャンネル (inbox, money, tasks, health, voice, files, etc.)
- 新システム： 3 チャンネルのみ + AI 自動分類
- `#memo` チャンネルですべてのコンテンツを受信（テキスト・音声・ファイル統合）
- AI が自動的に内容を分析してフォルダ分類
- 💰 Finance, ✅ Tasks, 🏃 Health, 🎙️ Voice Memos, 📁 Files 等は自動分類

### 6. 使用開始
**#memo チャンネルにメッセージを投稿するだけ！** AI が自動的に処理して適切なフォルダに保存します。

**🤖 AI 自動分類 & Obsidian フォルダ構造：**

**=== 日常使用フォルダ（高頻度・00-09番台）===**
- `"ちょっとメモ"` → 📥 `00_Inbox` （未分類・その他）
- `"今日の振り返り"` → 📅 `01_DailyNotes` （日記・日常記録）
- `"TODO: 資料作成"` → ✅ `02_Tasks` （タスク・やること）
- `"新しいアイデア"` → 💡 `03_Ideas` （アイデア・着想）

**=== 知識・学習系（中頻度・10-19番台）===**
- `"Python 学習メモ"` → 📚 `10_Knowledge` （学習・技術知識）
- `"プロジェクト進捗"` → 🚀 `11_Projects` （プロジェクト・仕事）
- `"参考資料"` → 📖 `12_Resources` （資料・参考文献）

**=== 記録・管理系（中頻度・20-29番台）===**
- `"1500 ランチ"` → 💰 `20_Finance` （家計・財務管理）
- `"体重 70kg"` → 🏃 `21_Health` （健康・運動記録）

**=== その他 ===**
- 音声ファイル → 🎙️ 自動文字起こし → 内容に応じた適切なフォルダ
- ファイル共有 → 📁 内容分析 → `80_Attachments` 系フォルダ

> **✨ 特徴：チャンネル ID 設定不要**
> 標準的なチャンネル名（`memo`, `notifications`, `commands`）で自動検出します。
> 面倒なチャンネル ID のコピペは不要です！

## ドキュメント

詳細な情報については、以下のドキュメントをご参照ください：

### 📚 ユーザー向け
- **[簡単セットアップガイド](docs/EASY_SETUP.md)** - 5 分セットアップガイド
- **[ローカルテスト手順](docs/LOCAL_TESTING.md)** - 開発・テスト環境での動作確認
- **[📁 Vault フォルダ構成ガイド](docs/VAULT_MIGRATION.md)** - 新フォルダ構成の詳細説明
- **[基本的な使い方](docs/user/basic-usage.md)** - 基本操作
- **[コマンドリファレンス](docs/user/commands-reference.md)** - 利用可能コマンド

### 🛠️ 開発者向け
- **[開発ガイド](docs/developer/development-guide.md)** - 開発環境構築
- **[アーキテクチャ](docs/developer/architecture.md)** - システム設計

### 🚀 運用者向け
- **[デプロイメント](docs/operations/deployment.md)** - 本番環境へのデプロイ
- **[トラブルシューティング](docs/operations/troubleshooting.md)** - 問題解決
- **[監視](docs/operations/monitoring.md)** - 監視とログ管理

## 主な特徴

### 🎯 ゼロ設定の自動化
メッセージを投稿するだけで、 AI が内容を分析し適切なフォルダに構造化して保存

### 🔄 シームレスな統合
Discord ↔ AI 処理 ↔ Obsidian の完全自動化されたワークフロー

### 🧠 インテリジェントな分類
機械学習による内容の自動分類とタグ付け

### 📊 包括的な管理
メモ、タスク、金融、健康データを一元管理

### 🔒 セキュリティ重視
Google Cloud Secret Manager による安全な認証情報管理

## サポートされる環境

- **開発**: ローカル開発環境（モックモード対応）
- **本番**: Google Cloud Run （ 24 時間 365 日稼働）
- **コンテナ**: Docker 対応
- **OS**: macOS, Linux, Windows （ WSL2 ）

## コミュニティとサポート

- **Issues**: [GitHub Issues](https://github.com/kenvexar/mindbridge/issues) でバグ報告・機能要求
- **Discussions**: プロジェクトについて議論
- **Documentation**: 包括的なドキュメントでサポート

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE) ファイルをご覧ください。

## 貢献

プロジェクトへの貢献を歓迎します！開発ガイドを参考に貢献してください。

---

**プロジェクト情報**
- バージョン: 0.1.0
- Python 要求バージョン: 3.13 以上
- メンテナー: Kent
- 最終更新: 2025 年 8 月 26 日
