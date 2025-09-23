# クイックスタート

MindBridge を最短 3 ステップでローカル実行できます。

> 📚 **より詳細な手順**: [インストールガイド](installation.md) を参照してください。

## 前提条件

- **Python 3.13+** がインストール済み
- **uv パッケージマネージャー** がインストール済み
- **Discord アカウント** と **Google Gemini API キー**

## 1. 依存関係インストール

```bash
uv sync --dev
```

## 2. 環境設定

### 対話式セットアップ（推奨）

```bash
./scripts/manage.sh init
```

### 手動セットアップ

```bash
cp .env.example .env
# .env ファイルを編集して以下を設定：
# - DISCORD_BOT_TOKEN
# - GEMINI_API_KEY
# - OBSIDIAN_VAULT_PATH
```

## 3. 起動

```bash
# 通常起動
uv run python -m src.main

# デバッグモード
uv run python -m src.main --debug
```

## 使用開始

起動後、 Discord で以下のチャンネルを作成：

- **#memo** - メイン入力チャンネル（テキスト・音声・ファイル）
- **#notifications** - システム通知
- **#commands** - Bot コマンド

**#memo** にメッセージを投稿すると、 AI が自動的に分析して Obsidian ノートを生成します！

## トラブルシューティング

| 問題 | 解決策 |
|------|--------|
| Bot が起動しない | `LOG_LEVEL=DEBUG` に設定して詳細ログを確認 |
| チャンネルが見つからない | チャンネル名が正確か確認（`memo`, `notifications`, `commands`） |
| Obsidian ファイルが作成されない | `OBSIDIAN_VAULT_PATH` のパスと権限を確認 |

## 次のステップ

- **[基本的な使用方法](basic-usage.md)** - 日常の使い方
- **[コマンドリファレンス](commands-reference.md)** - 利用可能なコマンド
- **[インストールガイド](installation.md)** - 詳細なセットアップ手順

## API キー取得（詳細手順）

Discord Bot と Gemini API キーの詳細な取得手順は [インストールガイド](installation.md) の各セクションを参照してください：

- **[Discord Bot セットアップ](installation.md#discord-bot-セットアップ)** - Bot 作成・権限設定・招待
- **[Gemini API 設定](installation.md#api-設定)** - API キー取得手順
