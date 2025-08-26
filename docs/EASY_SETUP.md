# 簡単セットアップガイド

Discord-Obsidian Memo Bot を 5 分で動かす最短手順です。

## 🚀 クイックスタート

### 1. 必要なもの

- Discord Bot トークン
- Google Gemini API キー
- Obsidian フォルダのパス

### 2. チャンネル作成（ 3 つだけ）

Discord サーバーに以下のテキストチャンネルを作成：

```
📝 memo           ← メモ投稿用（統合チャンネル・必須）
🔔 notifications  ← ボット通知用（必須）
🤖 commands       ← ボットコマンド用（必須）
```

### 3. 設定ファイル

```bash
# 設定例をコピー
cp .env.example .env

# 設定を編集
vim .env
```

**`.env`ファイルの必須項目:**

```env
DISCORD_BOT_TOKEN=あなたの Bot トークン
DISCORD_GUILD_ID=あなたの Discord サーバー ID
GEMINI_API_KEY=あなたの Gemini API キー
OBSIDIAN_VAULT_PATH=/path/to/obsidian/vault
```

### 4. 起動

```bash
uv run python -m src.main
```

### 5. 完了！

- `#memo`チャンネルにメッセージを投稿（すべてのタイプのコンテンツ対応）
- AI が内容を分析して適切なフォルダに自動分類
- ボットが自動的に処理して Obsidian に保存
- `#notifications`で処理状況を確認

## 🔧 追加チャンネル（オプション）

より多くの機能が欲しい場合は、以下のチャンネルを追加：

```
🎤 voice           ← 音声メモ
📎 files           ← ファイルアップロード
```

**注意**: `💰 money`, `✅ tasks` 等の機能は `#memo` チャンネルで統合されました。
AI が内容を自動分析してフォルダ分類するため、専用チャンネルは不要です。

**ボットを再起動すると自動的に検出されます。**

## 🏗️ Discord サーバー構成例

カテゴリで整理すると見やすくなります：

```
📝 MEMO SYSTEM (統合)
  ├── memo     ← 🆕 統合入力チャンネル（ Finance, Tasks, Health 等すべて）
  ├── voice
  └── files

🔧 SYSTEM
  ├── notifications
  ├── commands
  └── logs
```

**🆕 大幅な簡素化**:
- `memo` チャンネル 1 つですべてのコンテンツタイプを受信
- AI が自動分類: 💰 Finance, ✅ Tasks, 🏃 Health, 📚 Learning
- 専用チャンネル（ money, tasks 等）は不要

## ⚡ メリット

### 従来の複雑な方式
```env
# 😫 面倒だった...
CHANNEL_INBOX=123456789012345678
CHANNEL_VOICE=987654321098765432
CHANNEL_TASKS=456789123456789123
CHANNEL_NOTIFICATIONS=789123456789123456
# ... 10 個以上のチャンネル ID
```

### 現在のシンプルな方式
```env
# 😊 必要最小限で簡単！
DISCORD_BOT_TOKEN=your_token
DISCORD_GUILD_ID=your_guild_id
GEMINI_API_KEY=your_api_key
OBSIDIAN_VAULT_PATH=/path/to/vault
```

## 🔍 トラブルシューティング

### ボットがチャンネルを見つけられない

**症状:** ボットがチャンネルを認識しない

**解決方法:**
1. チャンネル名が正確か確認（`memo`, `notifications`, `commands`）
2. ボットにチャンネル表示権限があるか確認
3. `DISCORD_GUILD_ID`が正しいか確認

### ボットがメッセージに反応しない

**症状:** メッセージを投稿しても何も起こらない

**解決方法:**
1. ボットがオンラインか確認
2. ボットにメッセージ読み取り権限があるか確認
3. `#notifications`チャンネルでエラーメッセージを確認

### セットアップ状況の確認

ボット起動時のログで Discord チャンネル検出状況を確認：
```
INFO: Discord bot starting...
INFO: Found memo channel: 123456789
INFO: Found notifications channel: 987654321
INFO: Found commands channel: 456789123
```

## 📚 より詳しく

- **開発者向けドキュメント**: [CLAUDE.md](../CLAUDE.md)
- **プロジェクト概要**: [README.md](../README.md)
- **基本的な使い方**: [user/basic-usage.md](user/basic-usage.md)
