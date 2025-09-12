# 簡単セットアップガイド

MindBridge を 5 分で動かす最短手順です。

## 🚀 クイックスタート

### 1. 必要なもの

- Discord Bot トークン
- Google Gemini API キー
- Obsidian ボルトのパス

### 2. Discord サーバー設定（ 3 つだけ）

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

## 🎯 AI 自動分類システム

`#memo`チャンネルに投稿されたすべてのコンテンツ（テキスト、音声、ファイル）は AI により自動分類されます：

- **💰 Finance** → 「 1500 ランチ」「¥3000 本」などの支出情報
- **✅ Tasks** → 「 TODO: 資料作成」「期限: 明日まで」などのタスク
- **🏃 Health** → 「体重 70kg 」「ランニング 5km 」などの健康データ
- **📚 Learning** → 「 Python 学習」「読書メモ」などの学習記録
- **🎙️ Voice Memos** → 音声ファイルの自動文字起こし
- **📁 Files** → ファイル共有の適切なフォルダ分類
- **📝 Memos** → その他の一般的なメモ


## 🏗️ Discord サーバー構成例

カテゴリで整理すると見やすくなります：

```
📝 MEMO SYSTEM
  └── memo     ← 🆕 統合入力チャンネル（テキスト・音声・ファイルすべて対応）

🔧 SYSTEM
  ├── notifications  ← ボット通知
  └── commands       ← ボットコマンド
```

**🆕 大幅な簡素化**:
- `memo` チャンネル 1 つですべてのコンテンツタイプを受信（テキスト・音声・ファイル）
- AI が自動分類: 💰 Finance, ✅ Tasks, 🏃 Health, 📚 Learning, 🎙️ Voice, 📁 Files

## ⚡ メリット

### 従来の複雑な方式
```env
# 😫 面倒だった...
CHANNEL_INBOX=123456789012345678
CHANNEL_VOICE=987654321098765432
CHANNEL_FILES=456789123456789123
CHANNEL_MONEY=789123456789123456
CHANNEL_TASKS=456789123456789123
CHANNEL_HEALTH=789123456789123456
CHANNEL_NOTIFICATIONS=789123456789123456
# ... 17 個以上のチャンネル ID が必要だった
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

- **貢献ガイド**: [Repository Guidelines](../../AGENTS.md)
- **プロジェクト概要**: [README.md](../README.md)
- **基本的な使い方**: [user/basic-usage.md](user/basic-usage.md)
