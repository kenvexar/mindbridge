# クイックスタートガイド

**MindBridge を 10 分で起動する**

このガイドは 10 分以内に自動メモ処理を開始させるためのものです。

## ⏱️ 時間の内訳
- セットアップ: 2 分
- インストール: 3 分
- 設定: 3 分
- 起動とテスト: 2 分

## 📋 前提条件

開始前に以下を準備してください:

- [ ] Python 3.13+ がインストール済み
- [ ] Discord Bot トークン ([取得方法](#discord-bot-setup))
- [ ] Google Gemini API キー ([取得方法](#gemini-api-setup))
- [ ] Obsidian ボルト（または空のフォルダ）
- [ ] Discord サーバー（ボットを追加できるもの）

## 🏃‍♂️ クイックセットアップ

### 1. プロジェクトを取得 (1 分)

```bash
# リポジトリをクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# uv をインストール（まだインストールしていない場合）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 依存関係をインストール (2 分)

```bash
# 必要なパッケージをインストール
uv sync

# インストールを確認
uv run python --version  # Python 3.13+ が表示されるはず
```

### 3. 最小限の設定 (3 分)

```bash
# 設定テンプレートをコピー
cp .env.example .env
```

`.env` ファイルを編集して **4 つの必須設定だけ** を入力：

```env
# 必須設定（これだけで OK ！）
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_discord_server_id_here
GEMINI_API_KEY=your_gemini_api_key_here
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

### 4. テストボルトを作成 (30 秒)

```bash
# テストボルトフォルダを作成
mkdir -p ./test-vault
mkdir -p ./test-vault/{00_Inbox,01_DailyNotes,02_Tasks,03_Ideas}
mkdir -p ./test-vault/{10_Knowledge,11_Projects,12_Resources}
mkdir -p ./test-vault/{20_Finance,21_Health}
mkdir -p ./test-vault/{30_Archive,80_Attachments,90_Meta}

# .env をテストボルトパスで更新
echo "OBSIDIAN_VAULT_PATH=$(pwd)/test-vault" >> .env
```

### 5. Discord チャンネルを作成 (1 分)

Discord サーバーに以下の **3 つのチャンネルを正確に** 作成：
```
📝 memo           ← メイン入力チャンネル
🔔 notifications  ← システム通知
🤖 commands       ← ボットコマンド
```

**重要**: 正確なチャンネル名を使用してください (`memo`, `notifications`, `commands`) - ボットが自動検出します！

### 6. ボットを起動 (1 分)

```bash
# ボットを開始
uv run python -m src.main
```

✅ **成功の指標:**
```
INFO: Discord bot starting...
INFO: Found memo channel: 123456789
INFO: Found notifications channel: 987654321
INFO: Found commands channel: 456789123
INFO: Bot is ready! Logged in as YourBot#1234
```

### 7. 機能をテスト (2 分)

1. `#memo` チャンネルに移動
2. 以下のメッセージを投稿：

```
テスト投稿: 今日は良い天気です。プログラミングの勉強をします。
```

3. 10-30 秒待って、`test-vault` フォルダに新しい Markdown ファイルがあるか確認
4. `#commands` チャンネルで `/status` を実行してボットステータスを確認

## 🎉 成功！

おめでとうございます！ MindBridge が動作しています。以下が自動実行されます：
- AI で Discord メッセージを分析
- 構造化された Markdown ノートを生成
- AI 分類で Obsidian ボルトに保存
- 適切なフォルダにコンテンツを整理

## 📚 次のステップ

### すぐに試せる機能
- **音声メモ**: `#memo` に音声ファイルをアップロードして自動文字起こし
- **URL 分析**: URL を投稿して自動コンテンツ要約
- **コマンド**: `#commands` チャンネルで `/help` を試す

### さらに学ぶ
- **[基本的な使用方法](basic-usage.md)** - 日常使用ガイド
- **[インストールガイド](installation.md)** - 全機能の完全セットアップ
- **[コマンドリファレンス](commands-reference.md)** - 全コマンド一覧

## 🆘 API キーの取得

### Discord Bot セットアップ

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. "New Application" をクリック
3. アプリケーション名を入力（例："MindBridge Bot"）
4. "Bot" セクションに移動
5. "Add Bot" をクリック
6. "Token" をコピー（これが `DISCORD_BOT_TOKEN`）

**ボットをサーバーに追加:**
1. "OAuth2" → "URL Generator" に移動
2. スコープを選択: "bot" と "applications.commands"
3. ボット権限を選択:
   - Send Messages
   - Read Message History
   - Attach Files
   - Use Slash Commands
   - Message Content Intent (Bot 設定内)
4. 生成された URL でボットを招待

### Gemini API セットアップ

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. "Get API key" をクリック
3. "Create API key in new project" を選択
4. API キーをコピー（これが `GEMINI_API_KEY`）

### サーバー ID を取得

1. Discord で開発者モードを有効化:
   - 設定 → 高度な設定 → 開発者モード
2. サーバー名を右クリック → "ID をコピー"
3. これが `DISCORD_GUILD_ID`

## ❗ よくある問題

**ボットが応答しない:**
```bash
# ボットログを確認
tail -f logs/bot.log

# 設定を確認
cat .env | grep -E "(DISCORD_|GEMINI_|OBSIDIAN_)"
```

**権限エラー:**
```bash
# ボルト権限を確認
ls -la ./test-vault
chmod 755 ./test-vault
```

**依存関係エラー:**
```bash
# 依存関係を再インストール
uv sync --reinstall
```

**ボットがチャンネルを見つけられない:**
- 正確なチャンネル名を確認: `memo`, `notifications`, `commands`
- ボットがチャンネルを見る権限を持っているか確認
- `DISCORD_GUILD_ID` が正しいか確認

## 🧪 モックモードテスト

API キーがまだない場合は、モックモードでテストしてください:

```bash
# モックモードで実行（ API キー不要）
ENVIRONMENT=development ENABLE_MOCK_MODE=true uv run python -m src.main
```

## 📞 サポート

問題が発生した場合:
- [トラブルシューティングガイド](../operations/troubleshooting.md) を確認
- [GitHub Issues](https://github.com/kenvexar/mindbridge/issues) で問題を報告

---

このクイックスタートで基本機能を確認したら、[基本的な使用方法ガイド](basic-usage.md) で全機能を学んでください。
