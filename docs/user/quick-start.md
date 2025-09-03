# 🚀 クイックスタートガイド

**10分でMindBridgeを動かす最短手順**

このガイドに従えば、10分以内にBotを起動してメモの自動保存を開始できます。

## ⏱️ 時間配分
- 準備: 2分
- インストール: 3分
- 設定: 3分
- 起動・確認: 2分

## 📋 必要なもの

事前に以下を準備してください：

- [ ] Python 3.13以上がインストール済み
- [ ] Discord Botトークン ([取得方法](#discord-bot-の作成))
- [ ] Google Gemini APIキー ([取得方法](#gemini-api-キーの取得))
- [ ] Obsidianボルト（または空のフォルダ）
- [ ] Discordサーバー（ボットを追加できるもの）

## 🏃‍♂️ 最短手順

### 1. プロジェクトの取得 (1分)

```bash
# リポジトリのクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# uvのインストール（まだの場合）
curl -LsSf https://astral-sh/uv/install.sh | sh
```

### 2. 依存関係のインストール (2分)

```bash
# 必要なパッケージをインストール
uv sync

# インストール確認
uv run python --version  # Python 3.13以上が表示されることを確認
```

### 3. 最小限の設定 (3分)

```bash
# 設定ファイルをコピー
cp .env.example .env
```

`.env`ファイルを編集して以下の**4つの必須項目のみ**設定：

```env
# 必須設定（これだけでOK！）
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_discord_server_id_here
GEMINI_API_KEY=your_gemini_api_key_here
OBSIDIAN_VAULT_PATH=/Users/yourname/Documents/ObsidianVault

# 基本チャンネル（1つのチャンネルIDでテスト可能）
CHANNEL_INBOX=your_channel_id_here
```

### 4. テスト用Obsidianボルト作成 (30秒)

```bash
# テスト用ボルトフォルダを作成
mkdir -p ./test-vault
export OBSIDIAN_VAULT_PATH="$(pwd)/test-vault"

# .envファイルを更新
echo "OBSIDIAN_VAULT_PATH=$(pwd)/test-vault" >> .env
```

### 5. ボット起動 (1分)

```bash
# Botを起動
uv run python -m src.main
```

✅ **成功表示例：**
```
2025-08-17 10:30:15 - INFO - Bot is ready! Logged in as YourBot#1234
2025-08-17 10:30:15 - INFO - Listening to guild: Your Server Name
```

### 6. 動作テスト (2分)

1. 設定したDiscordチャンネルに移動
2. 以下のメッセージを投稿：

```
テスト投稿：今日は良い天気です。プログラミングの勉強をします。
```

3. 約10-30秒後、`test-vault`フォルダに新しいMarkdownファイルが作成されることを確認
4. Discordで`/status`コマンドを実行してボットの状態を確認

## 🎉 完了！

おめでとうございます！MindBridgeが正常に動作しています。

これで以下のことが自動化されます：
- Discordメッセージの自動AI分析
- 構造化されたMarkdownノートの生成
- Obsidianボルトへの自動保存
- 内容に基づく適切なフォルダ分類

## 📚 次のステップ

### すぐに使える機能
- **音声メモ**: 音声ファイルをアップロードすると自動文字起こし
- **URL解析**: URLを含むメッセージで自動コンテンツ要約
- **コマンド**: `/help`でコマンド一覧を確認

### さらに詳しく学ぶ
- **[基本的な使い方](basic-usage.md)** - 日常的な使用方法
- **[詳細インストール](installation.md)** - 全機能を使うための設定
- **[コマンドリファレンス](commands-reference.md)** - 全コマンド一覧

## 🆘 APIキーの取得方法

### Discord Bot の作成

1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. "New Application"をクリック
3. アプリケーション名を入力（例: "My Memo Bot"）
4. 左メニューから"Bot"を選択
5. "Add Bot"をクリック
6. "Token"をコピー（これが`DISCORD_BOT_TOKEN`）

**ボットをサーバーに追加：**
1. 左メニューから"OAuth2" → "URL Generator"
2. Scopesで"bot"と"applications.commands"を選択
3. Bot Permissionsで以下を選択：
   - Send Messages
   - Read Message History
   - Attach Files
   - Use Slash Commands
4. 生成されたURLでボットをサーバーに招待

### Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/)にアクセス
2. "Get API key"をクリック
3. "Create API key in new project"を選択
4. APIキーをコピー（これが`GEMINI_API_KEY`）

### チャンネルIDの取得

1. Discordで開発者モードを有効化：
   - 設定 → 詳細設定 → 開発者モード を有効
2. チャンネルを右クリック → "IDをコピー"
3. コピーしたIDを`CHANNEL_INBOX`に設定

## ❗ よくある問題

**ボットが反応しない**
```bash
# ボットのログを確認
tail -f logs/bot.log

# 設定を確認
cat .env | grep -E "(DISCORD_|GEMINI_|OBSIDIAN_)"
```

**権限エラー**
```bash
# Obsidianボルトの権限確認
ls -la ./test-vault
chmod 755 ./test-vault
```

**依存関係エラー**
```bash
# 依存関係を再インストール
uv sync --reinstall
```

## 🔧 モックモードでのテスト

実際のAPIキーがない場合は、モックモードでテストできます：

```bash
# モックモードで起動（APIキー不要）
ENVIRONMENT=development ENABLE_MOCK_MODE=true uv run python -m src.main
```

## 📞 サポート

問題が解決しない場合：
- [トラブルシューティング](../operations/troubleshooting.md)を確認
- [GitHub Issues](https://github.com/kenvexar/mindbridge/issues)で報告

---

このクイックスタートで基本的な動作を確認できたら、[基本的な使い方](basic-usage.md)で詳細な機能を学んでください。
